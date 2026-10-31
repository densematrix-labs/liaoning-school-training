import base64, io, random
from PIL import Image
from app.services.ai_gateway import bounded_vision_payload

def test_large_images_are_bounded_for_transmission_without_mutating_originals():
    randomizer=random.Random(7)
    image=Image.frombytes('RGB',(1400,1000),randomizer.randbytes(1400*1000*3))
    output=io.BytesIO();image.save(output,format='PNG')
    original='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
    messages=[{'role':'user','content':[{'type':'text','text':'参考图'},{'type':'image_url','image_url':{'url':original}},{'type':'text','text':'现场图'},{'type':'image_url','image_url':{'url':original}}]}]
    bounded=bounded_vision_payload(messages)
    assert messages[0]['content'][1]['image_url']['url']==original
    assert [x['text'] for x in bounded[0]['content'] if x['type']=='text']==['参考图','现场图']
    for part in [bounded[0]['content'][1],bounded[0]['content'][3]]:
        url=part['image_url']['url'];assert url.startswith('data:image/jpeg;base64,')
        data=base64.b64decode(url.split(',',1)[1]);assert len(data)<350000
        result=Image.open(io.BytesIO(data));assert max(result.size)<=1000
