"""
Admin cleanup: unregister unused models from Django Admin.

This module removes:
- Sites (django.contrib.sites) - not used, required only by allauth
- Social Accounts/Apps/Tokens (allauth.socialaccount) - managed via OAuth, not admin
- AuthToken (rest_framework.authtoken) - using JWT, not token auth

Import this module in urls.py AFTER admin.site.urls to ensure cleanup happens.
"""
from django.contrib import admin
from django.contrib.sites.models import Site

# Unregister Sites (required by allauth but not managed manually)
try:
    admin.site.unregister(Site)
except admin.sites.NotRegistered:
    pass

# Unregister allauth social account models
try:
    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
    admin.site.unregister(SocialAccount)
    admin.site.unregister(SocialApp)
    admin.site.unregister(SocialToken)
except (ImportError, admin.sites.NotRegistered):
    pass

# Unregister allauth account models (EmailAddress, EmailConfirmation)
try:
    from allauth.account.models import EmailAddress
    admin.site.unregister(EmailAddress)
except (ImportError, admin.sites.NotRegistered):
    pass

# Unregister DRF Token if registered
try:
    from rest_framework.authtoken.models import Token
    admin.site.unregister(Token)
except (ImportError, admin.sites.NotRegistered):
    pass
