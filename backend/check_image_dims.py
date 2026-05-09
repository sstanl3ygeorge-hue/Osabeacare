from routes.body_maps_data import BODY_MAP_MALE_PNG_B64, BODY_MAP_FEMALE_PNG_B64
import base64, io
from PIL import Image

male_bytes = base64.b64decode(BODY_MAP_MALE_PNG_B64)
female_bytes = base64.b64decode(BODY_MAP_FEMALE_PNG_B64)

male_img = Image.open(io.BytesIO(male_bytes))
female_img = Image.open(io.BytesIO(female_bytes))

print("Male image:", male_img.size, "(width x height)")
print("Orientation:", "landscape" if male_img.size[0] > male_img.size[1] else "portrait")
print()
print("Female image:", female_img.size, "(width x height)")
print("Orientation:", "landscape" if female_img.size[0] > female_img.size[1] else "portrait")
