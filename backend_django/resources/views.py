"""
API views for Resources (Documents and FAQ).
"""
import requests
from django.http import HttpResponse
from rest_framework import viewsets, views, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from elections.models import ConsultazioneElettorale
from .models import CategoriaDocumento, Documento, CategoriaFAQ, FAQ
from .serializers import (
    CategoriaDocumentoSerializer, DocumentoSerializer,
    CategoriaFAQSerializer, FAQSerializer, FAQListSerializer
)


class PDFProxyView(views.APIView):
    """
    Proxy per scaricare PDF esterni (evita problemi CORS).

    GET /api/risorse/pdf-proxy/?url=https://...

    Fetches the PDF from the external URL and serves it to the frontend.
    """
    permission_classes = [permissions.AllowAny]

    ALLOWED_DOMAINS = [
        'prefettura.interno.gov.it',
        'www.interno.gov.it',
        'interno.gov.it',
        'dait.interno.gov.it',
        'elezioni.interno.gov.it',
        'referendum.interno.gov.it',
    ]

    def get(self, request):
        url = request.query_params.get('url')

        if not url:
            return Response({'error': 'URL mancante'}, status=400)

        # Validate URL domain (security)
        from urllib.parse import urlparse
        parsed = urlparse(url)

        if parsed.netloc not in self.ALLOWED_DOMAINS:
            return Response({
                'error': f'Dominio non consentito: {parsed.netloc}'
            }, status=403)

        try:
            # Fetch PDF with timeout
            resp = requests.get(
                url,
                timeout=30,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; RDLApp/1.0)'
                },
                stream=True
            )
            resp.raise_for_status()

            # Check content type
            content_type = resp.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                return Response({
                    'error': 'Il contenuto non sembra essere un PDF'
                }, status=400)

            # Stream the response
            response = HttpResponse(
                resp.content,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = 'inline'
            response['Access-Control-Allow-Origin'] = '*'

            return response

        except requests.RequestException as e:
            return Response({
                'error': f'Errore nel recupero del PDF: {str(e)}'
            }, status=502)


class RisorseView(views.APIView):
    """
    GET /api/risorse/

    Restituisce tutte le risorse (documenti + FAQ) filtrate per la consultazione attiva.
    Raggruppa per categoria.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione')
        consultazione = None

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                pass

        # Filtra documenti
        documenti_qs = Documento.objects.per_consultazione(consultazione)
        if not request.user.is_authenticated:
            documenti_qs = documenti_qs.filter(is_pubblico=True)

        # Raggruppa documenti per categoria
        documenti_per_categoria = {}
        for doc in documenti_qs.select_related('categoria'):
            cat_nome = doc.categoria.nome if doc.categoria else 'Altro'
            cat_icona = doc.categoria.icona if doc.categoria else 'fa-file'
            cat_id = doc.categoria.id if doc.categoria else 0

            if cat_id not in documenti_per_categoria:
                documenti_per_categoria[cat_id] = {
                    'id': cat_id,
                    'nome': cat_nome,
                    'icona': cat_icona,
                    'documenti': []
                }
            documenti_per_categoria[cat_id]['documenti'].append(
                DocumentoSerializer(doc, context={'request': request}).data
            )

        # Filtra FAQ
        faqs_qs = FAQ.objects.per_consultazione(consultazione)
        if not request.user.is_authenticated:
            faqs_qs = faqs_qs.filter(is_pubblico=True)

        # Raggruppa FAQ per categoria
        faqs_per_categoria = {}
        for faq in faqs_qs.select_related('categoria'):
            cat_nome = faq.categoria.nome if faq.categoria else 'Generale'
            cat_icona = faq.categoria.icona if faq.categoria else 'fa-question-circle'
            cat_id = faq.categoria.id if faq.categoria else 0

            if cat_id not in faqs_per_categoria:
                faqs_per_categoria[cat_id] = {
                    'id': cat_id,
                    'nome': cat_nome,
                    'icona': cat_icona,
                    'faqs': []
                }
            faqs_per_categoria[cat_id]['faqs'].append(
                FAQSerializer(faq).data
            )

        return Response({
            'documenti': {
                'categorie': list(documenti_per_categoria.values()),
                'totale': documenti_qs.count(),
            },
            'faqs': {
                'categorie': list(faqs_per_categoria.values()),
                'totale': faqs_qs.count(),
            }
        })


class DocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet per i documenti (solo lettura).

    GET /api/risorse/documenti/ - Lista documenti
    GET /api/risorse/documenti/{id}/ - Dettaglio documento
    """
    serializer_class = DocumentoSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        consultazione_id = self.request.query_params.get('consultazione')
        consultazione = None

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                pass

        qs = Documento.objects.per_consultazione(consultazione)

        if not self.request.user.is_authenticated:
            qs = qs.filter(is_pubblico=True)

        # Filtri opzionali
        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria_id=categoria)

        return qs.select_related('categoria')


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet per le FAQ.

    GET /api/risorse/faqs/ - Lista FAQ
    GET /api/risorse/faqs/{id}/ - Dettaglio FAQ (incrementa visualizzazioni)
    POST /api/risorse/faqs/{id}/vota/ - Vota se utile
    """
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return FAQListSerializer
        return FAQSerializer

    def get_queryset(self):
        consultazione_id = self.request.query_params.get('consultazione')
        consultazione = None

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                pass

        qs = FAQ.objects.per_consultazione(consultazione)

        if not self.request.user.is_authenticated:
            qs = qs.filter(is_pubblico=True)

        # Filtri opzionali
        categoria = self.request.query_params.get('categoria')
        if categoria:
            qs = qs.filter(categoria_id=categoria)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(domanda__icontains=search) |
                Q(risposta__icontains=search)
            )

        return qs.select_related('categoria')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.incrementa_visualizzazioni()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def vota(self, request, pk=None):
        """
        POST /api/risorse/faqs/{id}/vota/
        Body: {"utile": true/false}
        """
        faq = self.get_object()
        utile = request.data.get('utile')

        if utile is None:
            return Response(
                {'error': 'Campo "utile" richiesto (true/false)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        faq.vota_utile(utile)
        return Response({
            'utile_si': faq.utile_si,
            'utile_no': faq.utile_no,
            'percentuale_utile': faq.percentuale_utile
        })
