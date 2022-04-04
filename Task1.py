import requests

host = 'http://geocode-maps.yandex.ru/1.x/'
params_query = {
    'apikey': 'bb8b1844-8ffd-4ac4-ab12-e879e77f924d',
    'geocode': input(),
    'format': 'json',
}

resp = requests.get(host, params=params_query)
if resp.status_code == 200:
    resp = resp.json()
    if int(resp["response"]["GeoObjectCollection"]["metaDataProperty"]["GeocoderResponseMetaData"]["found"]) > 0 :
        data = resp["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        print(f'Координаты: {data["Point"]["pos"]}')
        host = 'https://static-maps.yandex.ru/1.x/'
        params_query = {
            'll': str(data["Point"]["pos"]).replace(' ', ','),
            'spn': '0.016457,0.00619',
            'l': 'map',
        }
        resp = requests.get(host, params=params_query)
        if resp.status_code == 200:
            with open('map.png', mode='wb') as f:
                f.write(resp.content)
                print("Карта сохранена в map.png")
        else:
            print("Ошибка при получении изображения")
    else:
        print("Яндекс карты не знают о таком месте")
else:
    print("Все сломалось")