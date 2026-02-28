#!/usr/bin/env python3
"""
Identifica gli RDL che hanno sezioni vicine con sezioni spostate
e prepara il comando per ricalcolarle.

Le sezioni spostate sono quelle che hanno:
- Cambiato indirizzo (27 sezioni)
- Cambiato municipio (3 sezioni)
- Eliminate (7 sezioni: 9001-9007)
"""

# Sezioni spostate nel 2026
SEZIONI_SPOSTATE = {
    # Eliminate
    9001, 9002, 9003, 9004, 9005, 9006, 9007,
    # Cambio indirizzo
    173, 174, 175,
    1393, 1394, 1395, 1396,
    1714, 1715, 1717,
    1927, 1928, 1929, 1931, 1932,
    2071, 2072, 2073, 2074, 2075, 2097, 2280, 2405, 2475, 2476, 2477, 2554,
    # Cambio indirizzo + municipio
    2569, 2571, 2579,
}

print("=" * 80)
print("SEZIONI SPOSTATE NELLA RELEASE 2026")
print("=" * 80)
print()
print(f"Totale sezioni spostate: {len(SEZIONI_SPOSTATE)}")
print()
print("Sezioni eliminate (9001-9007):")
print("  9001, 9002, 9003, 9004, 9005, 9006, 9007")
print()
print("Sezioni con indirizzo cambiato (27 sezioni):")
print("  173, 174, 175")
print("  1393, 1394, 1395, 1396")
print("  1714, 1715, 1717")
print("  1927, 1928, 1929, 1931, 1932")
print("  2071, 2072, 2073, 2074, 2075, 2097, 2280, 2405, 2475, 2476, 2477, 2554")
print()
print("Sezioni con indirizzo + municipio cambiati (3 sezioni):")
print("  2569, 2571, 2579")
print()
print("=" * 80)
print("ISTRUZIONI PER RICALCOLARE I PLESSI VICINI DEGLI RDL")
print("=" * 80)
print()
print("Gli RDL che hanno tra i 'sezioni_vicine' una di queste sezioni spostate")
print("avranno indirizzi/municipi non più validi.")
print()
print("Per ricalcolare i plessi vicini per TUTTI gli RDL di Roma:")
print()
print("  docker-compose exec backend python manage.py ricalcola_plessi_vicini --comune-id 058091 --force")
print()
print("Opzioni:")
print("  --comune-id 058091  : Ricalcola solo per Roma (codice ISTAT)")
print("  --force             : Ricalcola anche RDL che hanno già sezioni_vicine")
print()
print("Per ricalcolare SOLO gli RDL geocodificati (senza sezioni_vicine):")
print()
print("  docker-compose exec backend python manage.py ricalcola_plessi_vicini")
print()
print("=" * 80)
