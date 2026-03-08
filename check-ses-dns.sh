#!/bin/bash

DOMAIN=$1
MAILFROM=$2

if [ -z "$DOMAIN" ]; then
  DOMAIN="ainaudi.it"
fi

if [ -z "$MAILFROM" ]; then
  MAILFROM="mail.ainaudi.it"
fi

echo "===================================="
echo "DNS CHECK FOR $DOMAIN"
echo "===================================="

echo ""
echo "SPF record:"
dig +short TXT $DOMAIN | grep "spf"

echo ""
echo "DMARC record:"
dig +short TXT _dmarc.$DOMAIN

echo ""
echo "MX records (root domain):"
dig +short MX $DOMAIN

echo ""
echo "DKIM selectors (SES):"

# SES uses unique hash-based selectors, not selector1/2/3
SES_DKIM_SELECTORS="a3fyltmm4tqrvrpnkoydbkvsqkogf7ka ou57oc3ut3xpcrnwiowwbchbfd7zulzt yyloxoodnzaxpoorh7e24onss3odnjpw"

for s in $SES_DKIM_SELECTORS; do
    echo -n "$s._domainkey.$DOMAIN -> "
    dig +short CNAME $s._domainkey.$DOMAIN
done

if [ ! -z "$MAILFROM" ]; then
  echo ""
echo "MAIL FROM domain: $MAILFROM"

echo ""
echo "MAIL FROM MX:"
dig +short MX $MAILFROM

echo ""
echo "MAIL FROM SPF:"
dig +short TXT $MAILFROM | grep spf
fi

echo ""
echo "===================================="
echo "CHECK COMPLETED"