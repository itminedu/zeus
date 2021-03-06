"""
Utilities for all views

Ben Adida (12-30-2008)
"""

from django.template import Context, Template, loader, TemplateSyntaxError, \
    TemplateDoesNotExist
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils import translation

import utils

from helios import datatypes

# nicely update the wrapper function
from functools import update_wrapper

import helios

from django.conf import settings

##
## BASICS
##

SUCCESS = HttpResponse("SUCCESS")

# FIXME: error code
FAILURE = HttpResponse("FAILURE")

##
## template abstraction
##
def prepare_vars(request, vars):
  vars_with_user = vars.copy()
  vars_with_user['user'] = getattr(request, 'zeususer', None)

  session = getattr(request, 'session', {})
  # csrf protection
  if session.has_key('csrf_token'):
    vars_with_user['csrf_token'] = session['csrf_token']

  vars_with_user['utils'] = utils
  vars_with_user['settings'] = settings
  vars_with_user['ZEUS_MEDIA_URL'] = '/static/zeus/booth/js'
  vars_with_user['TEMPLATE_BASE'] = helios.TEMPLATE_BASE
  vars_with_user['CURRENT_URL'] = request.path
  vars_with_user['SECURE_URL_HOST'] = settings.SECURE_URL_HOST
  #vars_with_user['voter'] = request.session.get('CURRENT_VOTER')

  trustee = None
  if session.has_key('helios_trustee_uuid') and not 'trustee' in vars:
    try:
        from helios.models import Trustee
        trustee = Trustee.objects.get(uuid=session.get('helios_trustee_uuid'))
        election = trustee.election
    except:
        try:
            del session['helios_trustee_uuid']
        except:
            pass

  vars_with_user['trustee'] = vars.get('trustee', trustee)

  return vars_with_user

def render_template(request, template_name, vars = {}, include_user=True):
  vars_with_user = prepare_vars(request, vars)

  language = translation.get_language().split('-')[0].lower()
  fallback_language = getattr(settings, 'I18N_TEMPLATES_FALLBACK_LANGUAGE', 'en')
  default_language = getattr(settings, 'LANGUAGE_CODE', 'en').split('-')[0].lower()

  if not include_user:
    del vars_with_user['user']

  dyn_tpl = '%s.html' % template_name
  dyn_tpl_i18n = 'i18n/%s/%s.html' % (language, template_name)
  dyn_tpl_fallback_i18n = 'i18n/%s/%s.html' % (fallback_language, template_name)
  dyn_tpl_default_i18n = 'i18n/%s/%s.html' % (default_language, template_name)
  i18n_tpl = 'helios/templates/i18n/%s/%s.html' % (language, template_name)
  template_name = 'helios/templates/%s.html' % template_name

  tpls = [dyn_tpl_i18n, dyn_tpl_fallback_i18n, dyn_tpl_default_i18n, dyn_tpl,
          i18n_tpl, template_name]
  tpls.reverse()
  tpl = None

  while not tpl:
    try:
        tpl = tpls.pop()
        loader.get_template(tpl)
    except (TemplateDoesNotExist, TemplateSyntaxError), e:
        tpl = None
        last_exc = e
    except IndexError:
        raise last_exc

  return render(request, tpl, vars_with_user)

def render_template_raw(request, template_name, vars={}):
  t = loader.get_template(template_name)

  # if there's a request, prep the vars, otherwise can't do it.
  if request:
    full_vars = prepare_vars(request, vars)
  else:
    full_vars = vars

  c = Context(full_vars)
  return t.render(c)


def render_json(json_txt):
  return HttpResponse(json_txt, "application/json")

# decorator
def json(func):
    """
    A decorator that serializes the output to JSON before returning to the
    web client.
    """
    def convert_to_json(self, *args, **kwargs):
      return_val = func(self, *args, **kwargs)
      try:
        return render_json(utils.to_json(return_val))
      except Exception, e:
        import logging
        logging.error("problem with serialization: " + str(return_val) + " / " + str(e))
        raise e

    return update_wrapper(convert_to_json,func)

