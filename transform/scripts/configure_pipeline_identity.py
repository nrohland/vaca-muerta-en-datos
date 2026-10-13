#!/usr/bin/env python3
"""Print the infrastructure plan by default. --apply performs persistent writes.

Uses the current gcloud/ADC login. Never creates service-account keys. No billing
changes. Requires an approved infrastructure plan before --apply.
"""
import argparse
import json
import subprocess

PROJECT = 'vaca-muerta-pulse'
NUMBER = '853495755275'
REPO = 'nrohland/vaca-muerta-pulse'
POOL = 'vm-data-dev'
PROVIDER = 'github-data-pipeline'
EXTRACT = f'vm-pulse-ci-extract-dev@{PROJECT}.iam.gserviceaccount.com'
DBT = f'vm-pulse-ci-dbt-dev@{PROJECT}.iam.gserviceaccount.com'
CONDITION = (
    "assertion.repository_id == '1364547377' && "
    "assertion.repository_owner_id == '55503418' && "
    "assertion.ref == 'refs/heads/main' && "
    "assertion.workflow_ref == 'nrohland/vaca-muerta-pulse/.github/workflows/data-pipeline.yml@refs/heads/main' && "
    "assertion.event_name in ['schedule', 'workflow_dispatch'] && "
    "assertion.environment in ['data-dev-extract', 'data-dev-dbt']"
)
PROVIDER_NAME = f'projects/{NUMBER}/locations/global/workloadIdentityPools/{POOL}/providers/{PROVIDER}'

def command(*args, exists=False):
    r = subprocess.run(['gcloud', *args, '--project='+PROJECT], capture_output=True, text=True)
    if r.returncode and not (exists and 'ALREADY_EXISTS' in r.stderr):
        raise RuntimeError(r.stderr)
    return r

def plan():
    return {
        'project': PROJECT, 'pool': POOL, 'provider': PROVIDER_NAME,
        'condition': CONDITION, 'new_accounts': [EXTRACT, DBT],
        'project_roles': {EXTRACT: ['roles/bigquery.jobUser'], DBT: ['roles/bigquery.jobUser']},
        'dataset_access': {
            'raw_cap4_candidate_dev': {'WRITER': EXTRACT, 'READER': DBT},
            **{name+'_cap4_candidate_dev': {'WRITER': DBT} for name in ['stg', 'int', 'marts']},
        },
        'github_variables': {'GCP_WIF_PROVIDER': PROVIDER_NAME, 'GCP_CI_EXTRACT_SA': EXTRACT,
                             'GCP_CI_DBT_SA': DBT, 'DATA_PIPELINE_ENABLED': 'false'},
        'federated_bindings': {EXTRACT: 'data-dev-extract', DBT: 'data-dev-dbt'},
        'keys_created': False, 'billing_changed': False, 'existing_roles_changed': False,
    }

def apply():
    from google.cloud import bigquery
    from google.api_core.exceptions import NotFound
    # Fail before any mutation if proposed names already exist; audit, do not adopt.
    for email in [EXTRACT, DBT]:
        r = subprocess.run(['gcloud', 'iam', 'service-accounts', 'describe', email, '--project='+PROJECT], capture_output=True, text=True)
        if r.returncode == 0 or 'NOT_FOUND' not in r.stderr:
            raise RuntimeError('Account exists or cannot be safely inspected: '+email)
    pools = json.loads(command('iam', 'workload-identity-pools', 'list', '--location=global', '--format=json').stdout)
    if any(row['name'].endswith('/'+POOL) for row in pools):
        raise RuntimeError('Pool already exists: audit its providers before applying')
    client = bigquery.Client(project=PROJECT, location='US')
    for name in plan()['dataset_access']:
        try:
            client.get_dataset(PROJECT+'.'+name)
        except NotFound:
            continue
        raise RuntimeError('Dataset already exists: audit permissions before applying '+name)
    command('services', 'enable', 'iam.googleapis.com', 'iamcredentials.googleapis.com', 'sts.googleapis.com')
    for email in [EXTRACT, DBT]:
        command('iam', 'service-accounts', 'create', email.split('@')[0], exists=True)
        command('projects', 'add-iam-policy-binding', PROJECT, '--member=serviceAccount:'+email,
                '--role=roles/bigquery.jobUser', '--condition=None')
    command('iam', 'workload-identity-pools', 'create', POOL, '--location=global', exists=True)
    # Existing providers are not silently changed: inspect them before rerunning.
    command('iam', 'workload-identity-pools', 'providers', 'create-oidc', PROVIDER,
            '--location=global', '--workload-identity-pool='+POOL,
            '--issuer-uri=https://token.actions.githubusercontent.com',
            '--attribute-mapping=google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.stage=assertion.environment',
            '--attribute-condition='+CONDITION)
    for email, stage in [(EXTRACT, 'data-dev-extract'), (DBT, 'data-dev-dbt')]:
        principal = f'principalSet://iam.googleapis.com/projects/{NUMBER}/locations/global/workloadIdentityPools/{POOL}/attribute.stage/{stage}'
        command('iam', 'service-accounts', 'add-iam-policy-binding', email,
                '--member='+principal, '--role=roles/iam.workloadIdentityUser')
    client = bigquery.Client(project=PROJECT, location='US')
    for name, access in plan()['dataset_access'].items():
        ds = bigquery.Dataset(PROJECT+'.'+name)
        ds.location = 'US'
        ds.default_table_expiration_ms = 60*24*60*60*1000
        client.create_dataset(ds, exists_ok=True)
        ds = client.get_dataset(ds)
        if ds.location != 'US':
            raise RuntimeError('Unexpected dataset location: '+name)
        entries = list(ds.access_entries)
        for role, email in access.items():
            entry = bigquery.AccessEntry(role, 'userByEmail', email)
            if entry not in entries: entries.append(entry)
        ds.access_entries = entries
        client.update_dataset(ds, ['access_entries'])
    for name, value in plan()['github_variables'].items():
        subprocess.run(['gh', 'variable', 'set', name, '--repo', REPO, '--body', value], check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(plan(), indent=2))
    if args.apply: apply()
