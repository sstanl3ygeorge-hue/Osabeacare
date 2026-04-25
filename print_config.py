import json
import sys
import os

# Add backend directory to path
sys.path.append('backend')

try:
    from care_certificate_config import CARE_CERTIFICATE_CONFIG
    
    results = []
    for item in CARE_CERTIFICATE_CONFIG:
        node = {
            'code': item.get('code'),
            'title': item.get('title'),
            'completion_type': item.get('completion_type'),
            'requires_signoff': item.get('admin_signoff_required'),
            'worker_action_available': item.get('worker_form_id') is not None,
            'worker_form_id': item.get('worker_form_id')
        }
        results.append(node)
    
    print(json.dumps(results, indent=2))
    print(f"Total item count: {len(results)}")

except ImportError as e:
    print(f"Error importing CARE_CERTIFICATE_CONFIG: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
