from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django import forms
from subprocess import Popen, PIPE
from functools import reduce
from .models import *
import pythonwhois
import paramiko
import json
import re

def get_whois_field(obj, field):
	try:
		whois_data = pythonwhois.net.get_whois_raw(obj, server='whois.dn42')
	except:
		raise ValidationError(_('Could not connect to dn42 whois servers.'))

	if len(whois_data) < 1:
		return None

	whois_data = whois_data[0].splitlines()

	values = list()
	for line in whois_data:
		line = line.strip()

		if not line or line.startswith('%'):
			continue

		key, value = line.split(':', maxsplit = 1)
		value = value.strip()

		if key == field:
			values.append(value)

	return values

@method_decorator(login_required, name='dispatch')
class PeeringView(ListView):
	model = Peering

	def get_queryset(self):
		return Peering.objects.filter(owner = self.request.user)

@method_decorator(login_required, name='dispatch')
class PeeringDetailView(DetailView):
	model = Peering

	def get_queryset(self):
		return Peering.objects.filter(owner = self.request.user)

class PeeringForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		self.user = kwargs.pop('user')
		super().__init__(*args, **kwargs)

	def clean_asn(self):
		mntby = get_whois_field('AS{}'.format(self.cleaned_data['asn']), 'mnt-by')
		if self.user.username not in mntby:
			raise ValidationError(_('User is not listed as mnt-by for this AS'))

		return self.cleaned_data['asn']

	def clean_endpoint_internal(self):
		mntby = get_whois_field('{}'.format(self.cleaned_data['endpoint_internal']), 'mnt-by')
		if self.user.username not in mntby:
			raise ValidationError(_('User is not listed as mnt-by for the internal router IP'))

		return self.cleaned_data['endpoint_internal']

	def clean_endpoint(self):
		if not re.match(r'^(\[[0-9a-f\:]+\]|([0-9]{1,3}\.){4}|[a-zA-Z\.]+)\:[0-9]{1,5}$', self.cleaned_data['endpoint']):
			raise ValidationError(_('Endpoint doesn\'t seem to be valid IP/hostname:port combo'))

		return self.cleaned_data['endpoint']

	def clean_wg_peer_pubkey(self):
		if len(self.cleaned_data['wg_peer_pubkey']) != 44:
			raise ValidationError(_('Wireguard public key has invalid length'))
		return self.cleaned_data['wg_peer_pubkey']

	class Meta:
		model = Peering
		fields = ['router', 'asn', 'vpn_type', 'endpoint', 'endpoint_internal', 'bandwidth_community', 'wg_peer_pubkey']

@method_decorator(login_required, name='dispatch')
class CreatePeeringView(CreateView):
	form_class = PeeringForm
	template_name = 'peeringmanager/peering_form.html'

	def get_queryset(self):
		return Peering.objects.filter(owner = self.request.user)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs.update({'user': self.request.user})
		return kwargs

	def form_valid(self, form):
		form.instance.owner = self.request.user

		with Popen(["wg", "genkey"], stdout=PIPE) as proc:
			privkey = proc.stdout.read()
			form.instance.wg_privkey = privkey.decode('utf-8').strip()

		with Popen(["wg", "pubkey"], stdout=PIPE, stdin=PIPE) as proc:
			pubkey = proc.communicate(input = privkey)[0]
			form.instance.wg_pubkey = pubkey.decode('utf-8').strip()

		form.instance.router.wg_last_port += 1
		form.instance.wg_port = form.instance.router.wg_last_port
		form.instance.router.save()

		fields = ['asn', 'endpoint', 'endpoint_internal', 'bandwidth_community', 'wg_privkey', 'wg_peer_pubkey', 'wg_port']
		data = map(lambda c: (c, getattr(form.instance, c)), fields)
		data = json.dumps(dict(data))

		ssh = paramiko.SSHClient()
		ssh.load_system_host_keys()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		key = paramiko.ed25519key.Ed25519Key.from_private_key_file(filename = '/tmp/autopeer.key')

		ssh.connect(form.instance.router.host_external, username = 'autopeer', banner_timeout = 5,
			look_for_keys = False, allow_agent = False, pkey = key)

		(stdin, stdout, stderr) = ssh.exec_command('/usr/bin/sudo /usr/local/bin/autopeer-modify')
		stdin.write(data + '\n')
		stdin.flush()
		print(stdout.read())
		print(stderr.read())
		ssh.close()

		return super().form_valid(form)