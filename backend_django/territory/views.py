"""
Views for territorio API endpoints.
"""
import csv
import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Regione, Provincia, Comune, Municipio, SezioneElettorale
from .serializers import (
    RegioneSerializer, RegioneWriteSerializer,
    ProvinciaSerializer, ProvinciaListSerializer, ProvinciaWriteSerializer,
    ComuneSerializer, ComuneListSerializer, ComuneWriteSerializer,
    MunicipioSerializer, MunicipioListSerializer, MunicipioWriteSerializer,
    SezioneElettoraleSerializer, SezioneElettoraleListSerializer, SezioneElettoraleWriteSerializer,
)
from .permissions import IsAdminForWriteOperations


class RegioneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Regione (full CRUD for admins, read-only for others).

    GET /api/territorio/regioni/
    GET /api/territorio/regioni/{id}/
    POST /api/territorio/regioni/           (admin only)
    PUT /api/territorio/regioni/{id}/       (admin only)
    PATCH /api/territorio/regioni/{id}/     (admin only)
    DELETE /api/territorio/regioni/{id}/    (admin only)
    POST /api/territorio/regioni/import_csv/ (admin only)
    """
    queryset = Regione.objects.all()
    permission_classes = [IsAdminForWriteOperations]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['statuto_speciale']
    search_fields = ['nome', 'codice_istat']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RegioneWriteSerializer
        return RegioneSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import regioni from CSV file.
        Expected columns: codice_istat, nome, statuto_speciale
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    codice_istat = row.get('codice_istat', '').strip()
                    nome = row.get('nome', '').strip()
                    statuto_speciale = row.get('statuto_speciale', '').strip().lower() in ['true', '1', 'si', 'sì', 'yes']

                    if not codice_istat or not nome:
                        errors.append(f"Riga {row_num}: codice_istat e nome sono obbligatori")
                        continue

                    obj, was_created = Regione.objects.update_or_create(
                        codice_istat=codice_istat,
                        defaults={'nome': nome, 'statuto_speciale': statuto_speciale}
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f"Riga {row_num}: {str(e)}")

            return Response({
                'created': created,
                'updated': updated,
                'total': created + updated,
                'errors': errors
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProvinciaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Provincia (full CRUD for admins, read-only for others).

    GET /api/territorio/province/
    GET /api/territorio/province/{id}/
    POST /api/territorio/province/           (admin only)
    PUT /api/territorio/province/{id}/       (admin only)
    PATCH /api/territorio/province/{id}/     (admin only)
    DELETE /api/territorio/province/{id}/    (admin only)
    POST /api/territorio/province/import_csv/ (admin only)
    """
    queryset = Provincia.objects.select_related('regione').all()
    permission_classes = [IsAdminForWriteOperations]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['regione', 'is_citta_metropolitana']
    search_fields = ['nome', 'sigla', 'codice_istat']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProvinciaWriteSerializer
        if self.action == 'list':
            return ProvinciaListSerializer
        return ProvinciaSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import province from CSV file.
        Expected columns: regione_codice, codice_istat, sigla, nome, is_citta_metropolitana
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    regione_codice = row.get('regione_codice', '').strip()
                    codice_istat = row.get('codice_istat', '').strip()
                    sigla = row.get('sigla', '').strip().upper()
                    nome = row.get('nome', '').strip()
                    is_citta_metropolitana = row.get('is_citta_metropolitana', '').strip().lower() in ['true', '1', 'si', 'sì', 'yes']

                    if not codice_istat or not nome or not sigla or not regione_codice:
                        errors.append(f"Riga {row_num}: tutti i campi sono obbligatori")
                        continue

                    try:
                        regione = Regione.objects.get(codice_istat=regione_codice)
                    except Regione.DoesNotExist:
                        errors.append(f"Riga {row_num}: Regione con codice {regione_codice} non trovata")
                        continue

                    obj, was_created = Provincia.objects.update_or_create(
                        codice_istat=codice_istat,
                        defaults={
                            'regione': regione,
                            'sigla': sigla,
                            'nome': nome,
                            'is_citta_metropolitana': is_citta_metropolitana
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f"Riga {row_num}: {str(e)}")

            return Response({
                'created': created,
                'updated': updated,
                'total': created + updated,
                'errors': errors
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ComuneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Comune (full CRUD for admins, read-only for others).

    GET /api/territorio/comuni/
    GET /api/territorio/comuni/{id}/      (accepts numeric ID or comune name)
    GET /api/territorio/comuni/{id}/sezioni/
    POST /api/territorio/comuni/           (admin only)
    PUT /api/territorio/comuni/{id}/       (admin only)
    PATCH /api/territorio/comuni/{id}/     (admin only)
    DELETE /api/territorio/comuni/{id}/    (admin only)
    POST /api/territorio/comuni/import_csv/ (admin only)
    """
    queryset = Comune.objects.select_related('provincia', 'provincia__regione').prefetch_related('municipi').all()
    permission_classes = [IsAdminForWriteOperations]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['provincia', 'provincia__regione', 'sopra_15000_abitanti']
    search_fields = ['nome', 'codice_istat', 'codice_catastale']
    # Allow both numeric IDs and names in URL
    lookup_value_regex = '[^/]+'

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ComuneWriteSerializer
        if self.action == 'list':
            return ComuneListSerializer
        return ComuneSerializer

    def get_object(self):
        """Override to accept both numeric ID and comune name."""
        lookup_value = self.kwargs.get(self.lookup_field)

        # Try numeric ID first
        try:
            pk = int(lookup_value)
            return self.queryset.get(pk=pk)
        except (ValueError, TypeError):
            pass
        except Comune.DoesNotExist:
            raise NotFound(f'Comune con ID {lookup_value} non trovato')

        # Try by name (case-insensitive)
        try:
            return self.queryset.get(nome__iexact=lookup_value)
        except Comune.DoesNotExist:
            raise NotFound(f'Comune "{lookup_value}" non trovato')

    @action(detail=True, methods=['get'])
    def sezioni(self, request, pk=None):
        """Get all electoral sections for a municipality."""
        comune = self.get_object()
        sezioni = comune.sezioni.filter(is_attiva=True).order_by('numero')
        serializer = SezioneElettoraleListSerializer(sezioni, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import comuni from CSV file.
        Expected columns: provincia_sigla, codice_istat, codice_catastale, nome, sopra_15000_abitanti
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    provincia_sigla = row.get('provincia_sigla', '').strip().upper()
                    codice_istat = row.get('codice_istat', '').strip()
                    codice_catastale = row.get('codice_catastale', '').strip().upper()
                    nome = row.get('nome', '').strip()
                    sopra_15000 = row.get('sopra_15000_abitanti', '').strip().lower() in ['true', '1', 'si', 'sì', 'yes']

                    if not codice_istat or not nome or not provincia_sigla or not codice_catastale:
                        errors.append(f"Riga {row_num}: codice_istat, codice_catastale, nome e provincia_sigla sono obbligatori")
                        continue

                    try:
                        provincia = Provincia.objects.get(sigla=provincia_sigla)
                    except Provincia.DoesNotExist:
                        errors.append(f"Riga {row_num}: Provincia con sigla {provincia_sigla} non trovata")
                        continue

                    obj, was_created = Comune.objects.update_or_create(
                        codice_istat=codice_istat,
                        defaults={
                            'provincia': provincia,
                            'codice_catastale': codice_catastale,
                            'nome': nome,
                            'sopra_15000_abitanti': sopra_15000
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f"Riga {row_num}: {str(e)}")

            return Response({
                'created': created,
                'updated': updated,
                'total': created + updated,
                'errors': errors
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MunicipioViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Municipio (full CRUD for admins, read-only for others).

    GET /api/territorio/municipi/
    GET /api/territorio/municipi/{id}/
    POST /api/territorio/municipi/           (admin only)
    PUT /api/territorio/municipi/{id}/       (admin only)
    PATCH /api/territorio/municipi/{id}/     (admin only)
    DELETE /api/territorio/municipi/{id}/    (admin only)
    POST /api/territorio/municipi/import_csv/ (admin only)
    """
    queryset = Municipio.objects.select_related('comune', 'comune__provincia').all()
    permission_classes = [IsAdminForWriteOperations]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['comune', 'comune__provincia']
    search_fields = ['nome', 'comune__nome']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MunicipioWriteSerializer
        if self.action == 'list':
            return MunicipioListSerializer
        return MunicipioSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import municipi from CSV file.
        Expected columns: comune_codice_istat, numero, nome
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    comune_codice_istat = row.get('comune_codice_istat', '').strip()
                    numero_str = row.get('numero', '').strip()
                    nome = row.get('nome', '').strip()

                    if not comune_codice_istat or not numero_str:
                        errors.append(f"Riga {row_num}: comune_codice_istat e numero sono obbligatori")
                        continue

                    try:
                        comune = Comune.objects.get(codice_istat=comune_codice_istat)
                    except Comune.DoesNotExist:
                        errors.append(f"Riga {row_num}: Comune con codice ISTAT {comune_codice_istat} non trovato")
                        continue

                    numero = int(numero_str)

                    obj, was_created = Municipio.objects.update_or_create(
                        comune=comune,
                        numero=numero,
                        defaults={'nome': nome}
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f"Riga {row_num}: {str(e)}")

            return Response({
                'created': created,
                'updated': updated,
                'total': created + updated,
                'errors': errors
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SezioneElettoraleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SezioneElettorale (full CRUD for admins, read-only for others).

    GET /api/territorio/sezioni/
    GET /api/territorio/sezioni/{id}/
    POST /api/territorio/sezioni/           (admin only)
    PUT /api/territorio/sezioni/{id}/       (admin only)
    PATCH /api/territorio/sezioni/{id}/     (admin only)
    DELETE /api/territorio/sezioni/{id}/    (admin only)
    POST /api/territorio/sezioni/import_csv/ (admin only)
    """
    queryset = SezioneElettorale.objects.select_related('comune', 'comune__provincia', 'municipio').all()
    permission_classes = [IsAdminForWriteOperations]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['comune', 'municipio', 'is_attiva', 'comune__provincia', 'comune__provincia__regione']
    search_fields = ['numero', 'comune__nome', 'indirizzo', 'denominazione']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SezioneElettoraleWriteSerializer
        if self.action == 'list':
            return SezioneElettoraleListSerializer
        return SezioneElettoraleSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import sezioni elettorali from CSV file.
        Expected columns: comune_codice_istat, municipio_numero, numero, indirizzo, denominazione, n_elettori, is_attiva
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Nessun file caricato'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    comune_codice_istat = row.get('comune_codice_istat', '').strip()
                    municipio_numero_str = row.get('municipio_numero', '').strip()
                    numero_str = row.get('numero', '').strip()
                    indirizzo = row.get('indirizzo', '').strip()
                    denominazione = row.get('denominazione', '').strip()
                    n_elettori_str = row.get('n_elettori', '').strip()
                    is_attiva_str = row.get('is_attiva', 'true').strip().lower()

                    if not comune_codice_istat or not numero_str:
                        errors.append(f"Riga {row_num}: comune_codice_istat e numero sono obbligatori")
                        continue

                    try:
                        comune = Comune.objects.get(codice_istat=comune_codice_istat)
                    except Comune.DoesNotExist:
                        errors.append(f"Riga {row_num}: Comune con codice ISTAT {comune_codice_istat} non trovato")
                        continue

                    municipio = None
                    if municipio_numero_str:
                        try:
                            municipio_numero = int(municipio_numero_str)
                            municipio = Municipio.objects.get(comune=comune, numero=municipio_numero)
                        except (ValueError, Municipio.DoesNotExist):
                            errors.append(f"Riga {row_num}: Municipio {municipio_numero_str} non trovato per {comune.nome}")
                            continue

                    numero = int(numero_str)
                    n_elettori = int(n_elettori_str) if n_elettori_str else None
                    is_attiva = is_attiva_str in ['true', '1', 'si', 'sì', 'yes', '']

                    obj, was_created = SezioneElettorale.objects.update_or_create(
                        comune=comune,
                        numero=numero,
                        defaults={
                            'municipio': municipio,
                            'indirizzo': indirizzo or None,
                            'denominazione': denominazione or None,
                            'n_elettori': n_elettori,
                            'is_attiva': is_attiva
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f"Riga {row_num}: {str(e)}")

            return Response({
                'created': created,
                'updated': updated,
                'total': created + updated,
                'errors': errors
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
