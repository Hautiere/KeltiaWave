#!/usr/bin/env python3
"""Configure OVH SMTP on staging through encrypted SSH; never send a message."""
import getpass
import json
import shlex
import subprocess
import sys

REMOTE = r'''
import json,sys,smtplib,ssl,os,shutil,subprocess
from pathlib import Path
credentials=json.load(sys.stdin)
try:
    with smtplib.SMTP_SSL('ssl0.ovh.net',465,timeout=20,context=ssl.create_default_context()) as smtp:
        smtp.login('contact@keltiawave.com', credentials['password'])
except Exception:
    print('Connexion SMTP refusée ou indisponible. Aucun paramètre modifié.')
    sys.exit(1)
p=Path('/home/ubuntu/apps/keltiawave/shared/.env.staging')
shutil.copy2(p,str(p)+'.before-smtp');os.chmod(str(p)+'.before-smtp',0o600)
values={'SMTP_HOST':'ssl0.ovh.net','SMTP_PORT':'465','SMTP_SECURITY':'ssl','SMTP_USERNAME':'contact@keltiawave.com','SMTP_PASSWORD':credentials['password'],'TRANSCRIPT_EMAIL_ENABLED':'true'}
lines=[line for line in p.read_text().splitlines() if line.split('=',1)[0] not in values]
def quote(value):
    return "'"+value.replace('\\','\\\\').replace("'","\\'")+"'"
lines.extend(key+'='+quote(value) for key,value in values.items())
p.write_text('\n'.join(lines)+'\n');os.chmod(p,0o600)
subprocess.run(['docker','compose','--env-file',str(p),'-f','docker-compose.candidate.yml','up','-d','--no-deps','backend'],cwd='/home/ubuntu/apps/keltiawave/releases/staging/deploy/ovh',check=True)
print('SMTP OVH configuré en staging. Aucun email envoyé. Vous pouvez tester depuis l’application.')
'''
if not sys.stdin.isatty():
    sys.exit('Lancez cette commande dans votre Terminal interactif.')
password = getpass.getpass('Mot de passe OVH de contact@keltiawave.com (saisie invisible) : ')
if not password or any(c in password for c in '\r\n\x00'):
    sys.exit('Mot de passe vide ou invalide ; aucune modification.')
result = subprocess.run(['ssh','-T','ubuntu@vps-dc75d8a6.vps.ovh.net','python3 -c '+shlex.quote(REMOTE)],input=json.dumps({'password':password}).encode())
sys.exit(result.returncode)
