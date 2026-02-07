#!/bin/bash
# Create test delegato for testing scrutinio aggregato

set -e

echo "=== CREATING TEST DELEGATO ==="
echo ""

docker exec rdl_backend python manage.py shell -c "
from core.models import User
from delegations.models import Delegato
from elections.models import ConsultazioneElettorale
from territory.models import Regione, Provincia, Comune

# Get or create test user
test_email = 'test.delegato@example.com'
test_user, created = User.objects.get_or_create(
    email=test_email,
    defaults={
        'first_name': 'Test',
        'last_name': 'Delegato',
        'is_active': True
    }
)
if created:
    test_user.set_unusable_password()
    test_user.save()
    print(f'✓ Created test user: {test_email}')
else:
    print(f'✓ Test user already exists: {test_email}')

# Get active consultation
cons = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
if not cons:
    print('✗ No active consultation found')
    exit(1)

print(f'✓ Active consultation: {cons.nome}')

# Check if delegato already exists
delegato = Delegato.objects.filter(email=test_email, consultazione=cons).first()

if delegato:
    print(f'✓ Delegato already exists for {test_email}')
else:
    # Create delegato
    delegato = Delegato.objects.create(
        consultazione=cons,
        cognome='Test',
        nome='Delegato',
        email=test_email,
        carica='RAPPRESENTANTE_PARTITO'
    )
    print(f'✓ Created Delegato: {delegato}')

# Add territory (Lazio region for testing)
lazio = Regione.objects.filter(nome__icontains='lazio').first()
if lazio:
    delegato.regioni.add(lazio)
    print(f'✓ Added territory: Regione {lazio.nome}')

    # Count sezioni in Lazio
    from territory.models import SezioneElettorale
    sezioni_count = SezioneElettorale.objects.filter(
        comune__provincia__regione=lazio
    ).count()
    print(f'  → {sezioni_count} sezioni in Lazio')
else:
    print('⚠ Regione Lazio not found, delegato has no territory')

print('')
print('=== TEST USER CREDENTIALS ===')
print(f'Email: {test_email}')
print(f'Password: (use magic link to login)')
print('')
print('To login:')
print('  1. Go to http://localhost:3000')
print('  2. Click \"Magic Link\"')
print(f'  3. Enter email: {test_email}')
print('  4. Check docker logs for magic link token')
print('')
"

echo "=== DONE ===""
