import asyncio
from db import mongo_client
from routes.body_maps import _render_body_map_pdf

async def check():
    db = mongo_client['osabeacare']
    records = list(db['body_maps'].find().sort('_id', -1).limit(1))
    for rec in records:
        print('Latest body map:')
        print(f'  Service user: {rec.get("service_user_name")}')
        gender_val = rec.get("gender")
        print(f'  Gender: "{gender_val}"')
        print(f'  Gender type: {type(gender_val).__name__}')
        print(f'  Gender repr: {repr(gender_val)}')
        
        # Check normalization
        raw_gender = (gender_val or "").strip().lower()
        print(f'  Normalized: "{raw_gender}"')

asyncio.run(check())
