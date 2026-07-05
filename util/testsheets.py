import gspread
from google.oauth2.service_account import Credentials

creds_dict = {
  "type": "service_account",
  "project_id": "invigilator-app-501412",
  "private_key_id": "21e4f892b5115da087f9f8ed4e5799d41daf4f70",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDVxqORp9YVzAb/\n8KCrtYbnT3foo+mbePZyZX5wPO8zVKbRyUXneOGJtngzZGYA/cksJ0mwpsr85mLN\nVQQXwNMbfwICbPCWDXDRYX5nDpiq3aiYGOE67CjHtF1MngcqEpJP+JpEWlPJX+3s\n47Wr1NJy8U5L1Kcp8D1ini5GL+ZcXLAI+Q+73xexaZ33hC3gCectoGS8eicAtv7S\nIEo4/Ok/Odx7Ad61LWc07mA8h/0zD1jVPp7Qb28E/eLCFP6ck+yylibuZHISKtPU\no4m4Dk3HJ9TFUFmuF9TiLVWemyZxZfra/ELAlzgI9W3SMiJmT+msYOD+De3CXwi+\nLCLua/2zAgMBAAECggEAVsMQZtDF8EHGw4B/TUFW97FGmspPyRRefY5Ysyff8ybT\nr8gvEWN7sf83KLCCP7vAtqVZYJNJRjwg9HIhP5y4cWvqPl7FhDj/RVN60EvZxVtC\nDjzmyJnJcUfwJ+TpRneUH1XoEn7Qi6Xd9Ct088DkCteJ7ffoQnqpB0nowP620Vvk\nsooXVrM4ulm6BdLSJcMjvZtGSiIXiqtwpn+2up2cnHLP9xCtcT0ZvUJvPP5YQrAn\nv3tDk4N8oHg584tAyiUi+kEfHLsw3SzFDSeoVh6leSlFcwUXBzsF4Gdqo7szG5Zo\nNIP6gUkGchNq0RqHNH0CQjRw28o4L09PkRe6QrHh8QKBgQD4Nxa37DE0Gt+JtNDP\nJ6f6wsDZ4Gqc8oIegMLfaeno8ytoGNhNNEYpn2tncav0Xi2I4PRNzh9g5YWLw+o8\nohQfTWC380wSZaGcenu0jwvU9uWiSzrR4M8HK2pNHkBCiaWQqtFaMHOPS2qeVCLs\n9nMMi72ufjmI8cscx9zPTpgvowKBgQDcewngkvUBgp8nRz17u5lj2z6//3iDXScM\nI6UAuSzK/GAHXeM/AwmBHcyTdeISTUbsmIPIzcV6kY1J3L5d9yaMIchZfFdRVaiC\nKP25oFhjzgrl4G6HWexkVHytTBcWI1yIXK38WAhKE58F8YNIhbuLvCebbK5Gm4+M\nbKkox/masQKBgBwj8rlrV7C2kz1DeKDjuBGf3slUvgGJJONcabt2gIRefT9SAcPO\n911kq4KQypPr0XHBPzFK+xe7LcbIsVeqcGmUFjEErk0vpIDfCgNQbGD6lNIvgT2m\nJRKFA4o2scZZYKHkG9QDxjYqsK2+kC8ZSbXUae7MdK1n7EUZC5mdKXfNAoGBAKjZ\nmXDhWr0zWcts5Ysy2n/80gucDKEd39+OFLl/FuzFZo19u6DwJIE7Xwa3StEVWXGs\nQ5Cu9cOuYHPml+vCcUT0Qkk1znE9lnVICzfzsn2MuA/gVwVVOpKDmY/mK/AKWL0d\nrSkKCh8g87JLiW0q7bxP9k0zaCwuyjqSpOHUdDWhAoGAQ+XCBbJN+HMAig7EghT5\njGfCwlOjhGQaZOadd5VqpEMCW1vNLunEWVfAKgF6cohskLIRBQMs2lQlA8hvICh7\nCiRtG69wougu5GL7yYGzuJyFcm4eVyxbi1IlP9m86jKAmb3XLkkZ6E0cR1Bjtjv4\nlgPPPfD3kjtduWILEu3l4Kc=\n-----END PRIVATE KEY-----\n",
  "client_email": "sheetseditor@invigilator-app-501412.iam.gserviceaccount.com",
  "client_id": "116019394209727189887",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sheetseditor%40invigilator-app-501412.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

try:
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    client = gspread.authorize(creds)
    sheet = client.open("Invigilator Signups")
    print("✅ Connected successfully!")
    print(f"Sheet: {sheet.title}")
except Exception as e:
    print(f"❌ Error: {e}")