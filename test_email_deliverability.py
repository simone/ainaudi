#!/usr/bin/env python3
"""
Test automatico della configurazione email (SPF, DKIM, DMARC) per evitare spam.

Usage:
    python3 test_email_deliverability.py ainaudi.it noreply@ainaudi.it
    python3 test_email_deliverability.py ainaudi.it noreply@ainaudi.it --verbose
"""

import sys
import dns.resolver
import boto3
import argparse
from datetime import datetime


class EmailDeliverabilityTest:
    def __init__(self, domain, from_email, verbose=False):
        self.domain = domain
        self.from_email = from_email
        self.verbose = verbose
        self.results = {}
        self.warnings = []
        self.errors = []

    def test_dns_record(self, record_type, name):
        """Testa un record DNS."""
        try:
            answers = dns.resolver.resolve(name, record_type)
            if self.verbose:
                print(f"✓ {record_type} record trovato per {name}")
            return [str(rdata) for rdata in answers]
        except Exception as e:
            if self.verbose:
                print(f"✗ {record_type} record non trovato per {name}: {e}")
            return None

    def check_spf(self):
        """Controlla record SPF."""
        print("\n" + "="*80)
        print("1️⃣  SPF (Sender Policy Framework)")
        print("="*80)

        spf_records = self.test_dns_record('TXT', self.domain)
        if not spf_records:
            self.errors.append("SPF: Nessun record TXT trovato")
            return False

        spf_record = None
        for record in spf_records:
            # Handle both single string and quoted/combined strings
            record_clean = record.strip('"')
            if 'v=spf1' in record_clean:
                spf_record = record_clean
                break

        if not spf_record:
            self.errors.append("SPF: Record SPF non trovato")
            return False

        print(f"✓ Record SPF trovato: {spf_record}")

        checks = {
            'include:amazonses.com': 'Amazon SES incluso',
            '-all': 'Usa -all (restrittivo) ✓',
            '~all': 'Usa ~all (permissivo) ⚠️',
        }

        found_checks = {}
        for check, desc in checks.items():
            if check in spf_record:
                found_checks[check] = desc
                print(f"  ✓ {desc}")

        if 'include:amazonses.com' not in spf_record:
            self.errors.append("SPF: Manca include:amazonses.com")
            print(f"  ✗ ERRORE: Manca include:amazonses.com")
            return False

        if '~all' in spf_record and '-all' not in spf_record:
            self.warnings.append("SPF: Usa ~all invece di -all (meno restrittivo)")
            print(f"  ⚠️  AVVISO: Usa ~all. Meglio cambiare con -all")

        if spf_record.count('v=spf1') > 1:
            self.errors.append("SPF: Record SPF duplicati")
            print(f"  ✗ ERRORE: Record SPF duplicati")
            return False

        self.results['spf'] = 'OK'
        return True

    def check_dkim(self):
        """Controlla record DKIM."""
        print("\n" + "="*80)
        print("2️⃣  DKIM (DomainKeys Identified Mail)")
        print("="*80)

        # Prova selettori standard e selettori custom di AWS
        selectors = ['default', 'amazon', 'amazonses']

        dkim_found = False
        for selector in selectors:
            dkim_name = f"{selector}._domainkey.{self.domain}"
            dkim_records = self.test_dns_record('CNAME', dkim_name)

            if dkim_records:
                print(f"✓ DKIM record trovato per selettore '{selector}':")
                for record in dkim_records:
                    print(f"  {dkim_name} -> {record}")
                dkim_found = True

        # Se non trovi selettori standard, accetta custom selettori di AWS
        if not dkim_found:
            # Prova a cercare i DKIM records custom (lunghi hash di AWS)
            import subprocess
            try:
                # Usa gcloud per cercare tutti i CNAME sotto _domainkey
                result = subprocess.run(
                    ['gcloud', 'dns', 'record-sets', 'list',
                     '--zone=ainaudi-zone' if 'ainaudi.it' in self.domain else '',
                     '--filter=type:CNAME AND name:*._domainkey*',
                     '--format=value(data)'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and 'dkim.amazonses.com' in result.stdout:
                    print(f"✓ DKIM configurato con selettori custom di AWS SES")
                    dkim_found = True
                else:
                    # Fallback: prova dig su ciascuno dei record CNAME specifici
                    cname_checks = [
                        'a3fyltmm4tqrvrpnkoydbkvsqkogf7ka._domainkey.ainaudi.it',
                        'ou57oc3ut3xpcrnwiowwbchbfd7zulzt._domainkey.ainaudi.it',
                        'yyloxoodnzaxpoorh7e24onss3odnjpw._domainkey.ainaudi.it',
                    ]
                    for cname in cname_checks:
                        result2 = subprocess.run(
                            ['dig', cname, 'CNAME', '+short'],
                            capture_output=True, text=True, timeout=5
                        )
                        if 'dkim.amazonses.com' in result2.stdout:
                            print(f"✓ DKIM configurato (record trovato: {cname})")
                            dkim_found = True
                            break
            except:
                pass

        if not dkim_found:
            self.errors.append("DKIM: Nessun record DKIM trovato")
            print("✗ ERRORE: Nessun record DKIM trovato")
            print("\nDevi abilitare DKIM su Amazon SES:")
            print("  1. Vai a AWS SES Console")
            print("  2. Seleziona il dominio 'ainaudi.it'")
            print("  3. Clicca 'DKIM' -> 'Generate DKIM Settings'")
            print("  4. Aggiungi i 3 record CNAME al DNS")
            return False

        self.results['dkim'] = 'OK'
        return True

    def check_dmarc(self):
        """Controlla record DMARC."""
        print("\n" + "="*80)
        print("3️⃣  DMARC (Domain-based Message Authentication, Reporting & Conformance)")
        print("="*80)

        dmarc_name = f"_dmarc.{self.domain}"
        dmarc_records = self.test_dns_record('TXT', dmarc_name)

        if not dmarc_records:
            self.warnings.append("DMARC: Record DMARC non trovato")
            print(f"⚠️  AVVISO: Record DMARC non trovato")
            print(f"\nTi consiglio di aggiungere:")
            print(f"  Nome: _dmarc.{self.domain}")
            print(f"  Tipo: TXT")
            print(f"  Valore: v=DMARC1; p=quarantine; rua=mailto:dmarc@{self.domain}; adkim=s; aspf=s")
            self.results['dmarc'] = 'MISSING'
            return False

        dmarc_record = None
        for record in dmarc_records:
            record_clean = record.strip('"')
            if 'v=DMARC1' in record_clean:
                dmarc_record = record_clean
                break

        if not dmarc_record:
            self.warnings.append("DMARC: Record DMARC malformato")
            print(f"⚠️  AVVISO: Record TXT trovato ma non è DMARC: {dmarc_records[0]}")
            return False

        print(f"✓ Record DMARC trovato: {dmarc_record}")

        # Analizza il record DMARC
        if 'p=none' in dmarc_record:
            self.warnings.append("DMARC: Policy=none (troppo permissiva)")
            print(f"  ⚠️  Policy=none: accetta tutto, non proteggere. Meglio p=quarantine")
        elif 'p=quarantine' in dmarc_record:
            print(f"  ✓ Policy=quarantine: buon compromesso")
        elif 'p=reject' in dmarc_record:
            print(f"  ✓ Policy=reject: massima protezione")

        if 'rua=' not in dmarc_record:
            self.warnings.append("DMARC: Manca email per report (rua=)")
            print(f"  ⚠️  Manca rua= per ricevere report")

        if 'adkim=s' in dmarc_record:
            print(f"  ✓ adkim=s (DKIM alignment strict)")
        else:
            self.warnings.append("DMARC: adkim non strict")
            print(f"  ⚠️  adkim non strict (usa adkim=s)")

        if 'aspf=s' in dmarc_record:
            print(f"  ✓ aspf=s (SPF alignment strict)")
        else:
            self.warnings.append("DMARC: aspf non strict")
            print(f"  ⚠️  aspf non strict (usa aspf=s)")

        self.results['dmarc'] = 'OK'
        return True

    def check_reverse_dns(self):
        """Controlla reverse DNS."""
        print("\n" + "="*80)
        print("4️⃣  Reverse DNS")
        print("="*80)

        print(f"ℹ️  Reverse DNS per dominio {self.domain}:")
        print(f"  Dipende dal provider hosting / IP")
        print(f"  Se usi Amazon SES con IP condiviso, contatta AWS Support")
        print(f"  Best practice: Usa IP dedicato + custom MAIL FROM")

        self.results['reverse_dns'] = 'MANUAL_CHECK'

    def check_ses_configuration(self):
        """Controlla configurazione Amazon SES."""
        print("\n" + "="*80)
        print("5️⃣  Amazon SES Configuration")
        print("="*80)

        try:
            # Nota: Richiede AWS credentials configurate
            client = boto3.client('ses', region_name='eu-west-3')  # Parigi

            # Verifica dominio
            domains = client.list_verified_email_addresses()
            identities = client.list_identities()

            if self.domain in identities['Identities']:
                print(f"✓ Dominio '{self.domain}' verificato in SES")

                # Verifica attributi DKIM
                attrs = client.get_identity_dkim_attributes(Identities=[self.domain])
                dkim_attrs = attrs['DKIMAttributes'].get(self.domain, {})

                if dkim_attrs.get('DKIMEnabled'):
                    if dkim_attrs.get('DKIMVerificationStatus') == 'Success':
                        print(f"  ✓ DKIM enabled e verified")
                        self.results['ses_dkim'] = 'VERIFIED'
                    else:
                        self.warnings.append(f"SES: DKIM non verified (status: {dkim_attrs.get('DKIMVerificationStatus')})")
                        print(f"  ⚠️  DKIM enabled ma status: {dkim_attrs.get('DKIMVerificationStatus')}")
                else:
                    self.errors.append("SES: DKIM non abilitato")
                    print(f"  ✗ DKIM non abilitato")

                # Verifica SPF/DKIM tokens
                if 'DKIMTokens' in dkim_attrs:
                    print(f"  DKIM Tokens: {dkim_attrs['DKIMTokens']}")

            else:
                self.errors.append(f"SES: Dominio '{self.domain}' non verificato")
                print(f"✗ Dominio '{self.domain}' non trovato in SES")
                print(f"  Devi verificare il dominio in AWS SES Console")

        except Exception as e:
            self.warnings.append(f"SES: Non posso verificare - {str(e)}")
            print(f"⚠️  Impossibile verificare SES (AWS credentials non configurate?)")
            print(f"  Verifica manualmente in AWS SES Console")

    def check_mail_from_domain(self):
        """Controlla Mail FROM Domain."""
        print("\n" + "="*80)
        print("6️⃣  Custom MAIL FROM Domain")
        print("="*80)

        print(f"ℹ️  Configurazione avanzata (opzionale ma consigliata):")
        print(f"  Nome dominio: {self.domain}")
        print(f"  Mail From: bounce@{self.domain}")
        print(f"\nNel DNS aggiungi MX record:")
        print(f"  Nome: bounce.{self.domain}")
        print(f"  Tipo: MX")
        print(f"  Valore: 10 feedback-smtp.<region>.amazonses.com")
        print(f"  (Sostituisci <region> con la tua AWS region, es. eu-west-3 per Parigi)")

        self.results['mail_from'] = 'OPTIONAL'

    def run_all_tests(self):
        """Esegui tutti i test."""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "  🧪 EMAIL DELIVERABILITY TEST".ljust(78) + "║")
        print("║" + f"  Dominio: {self.domain} | From: {self.from_email}".ljust(78) + "║")
        print("║" + f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "="*78 + "╝")

        self.check_spf()
        self.check_dkim()
        self.check_dmarc()
        self.check_reverse_dns()
        self.check_ses_configuration()
        self.check_mail_from_domain()

        self.print_summary()

    def print_summary(self):
        """Stampa il riassunto finale."""
        print("\n" + "="*80)
        print("📊 RIASSUNTO FINALE")
        print("="*80)

        print(f"\n✓ Tests OK: {list(self.results.keys())}")

        if self.warnings:
            print(f"\n⚠️  Avvisi ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print(f"\n✗ Errori ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print(f"\n✓ Nessun errore critico!")

        # Score
        score = 100
        score -= len(self.errors) * 25
        score -= len(self.warnings) * 10
        score = max(0, min(100, score))

        print(f"\n📈 Deliverability Score: {score}/100")

        if score >= 90:
            print("  ✓ Eccellente - Email dovrebbe arrivare in Inbox")
        elif score >= 70:
            print("  ⚠️  Buono - Qualche miglioramento consigliato")
        else:
            print("  ✗ Insufficiente - Rischio di spam/bounce alto")

        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Test automatico configurazione email (SPF, DKIM, DMARC)'
    )
    parser.add_argument('domain', help='Dominio da testare (es. ainaudi.it)')
    parser.add_argument('from_email', help='Email mittente (es. noreply@ainaudi.it)')
    parser.add_argument('--verbose', action='store_true', help='Output verboso')

    args = parser.parse_args()

    tester = EmailDeliverabilityTest(args.domain, args.from_email, args.verbose)
    tester.run_all_tests()


if __name__ == '__main__':
    main()
