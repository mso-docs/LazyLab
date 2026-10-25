"""Actionable local readiness checks; never download or fabricate a model."""
import importlib.metadata
import json
import platform
from urllib.request import urlopen
from slothlab.experiments.isolation import isolation_status


def diagnose(config, check_model=True):
    result={'python':platform.python_version(),'dependencies':{},'isolation':isolation_status(),'model':{'configured':config.model,'base_url':config.base_url,'checked':check_model},'ready':True}
    for package in ('pydantic','numpy','pandas','scikit-learn','psutil'):
        try:
            result['dependencies'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result['dependencies'][package]=None
            result['ready']=False
    if config.execution_isolation=='bubblewrap' and not result['isolation']['available']:
        result['ready']=False
    if check_model:
        try:
            with urlopen(config.base_url.rstrip('/')+'/api/tags',timeout=5) as response:
                body=json.load(response)
            installed=[item['name'] for item in body.get('models',[])]
            result['model']['installed']=installed
            result['model']['available']=bool(config.model and config.model in installed)
            if not result['model']['available']:
                result['ready']=False
                result['model']['error']='Select an installed model with OLLAMA_MODEL or the dashboard model field'
        except (OSError,ValueError,KeyError) as exc:
            result['model']['error']=f'Start Ollama and verify OLLAMA_BASE_URL: {exc}'
            result['ready']=False
    return result
