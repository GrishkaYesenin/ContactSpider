import csv
import os
import requests
from bs4 import BeautifulSoup as BS

HOST = 'https://zakupki.gov.ru'

URL = 'https://zakupki.gov.ru/epz/order/extendedsearch/search.html'

HEADERS = {
    "accept": "*/*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) /"
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
}

FEATURES = {
    'Сокращенное наименование': 'Поставщик',
    'Адрес электронной почты': 'email',
    'Контактный адрес электронной почты': 'email',
    'Контактные телефоны': 'Телефон',
    'Телефон': 'Телефон',
    'Контактное лицо': 'Контактное лицо',
    'Адрес организации в сети Интернет': 'Сайт'
            }

HEADERS_SHEET = ['Поставщик', 'Приоритет', 'Телефон', 'email', 'Сайт', 'Сфера деятельности', 'Комментарии',
                 'Ссылка на продукт ', 'Сегмент', 'Что предлагаем', 'Письмо (дата)', 'Комментарий менеджера (дата)',
                 'Ссылка битрикс', 'Статус', 'Рабочий номер', 'Рабочий Email', 'Контактное лицо', 'Должность']


def exists(path: str) -> bool:
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def if_correct_address(address: str, city: str) -> bool:
    if not city:
        return True
    if address.find(city) == -1:
        return False
    else:
        return True


def preparing_data():
    """
    Singles out the city from the name and writes it in a separate column
    """

    with open('data.csv') as dataFile:

        with open('preparingData.csv', 'w', newline='') as preparingDataFile:
            writer = csv.DictWriter(preparingDataFile, fieldnames=('name', 'city'))
            writer.writeheader()
            reader = csv.reader(dataFile, delimiter=',')
            for row in reader:
                try:
                    for organization in row[0].split('\n'):
                        name, *city = organization.split(',')
                        if name not in ('', 'Поставщик'):
                            if city:
                                city = city[0].strip('г. ')
                            writer.writerow({'name': name, 'city': city})
                except Exception as e:
                    print(f'{e} in preparing_data')


class ContactSpider():

    def __init__(self):
        print('---Parser initialization---')

    def make_soup(self, url=URL):
        req = requests.get(url=url, headers=HEADERS)
        soup = BS(req.text, 'lxml')
        return soup

    def find_organizations_by_city(self, soup, city: str) -> list:
        """
        Finding in the soup html organizations with a suitable address (with the same city)
        """

        print('---Find_organizations_by_city---')
        organizations = []

        organization_list_block = soup.find(id="chooseOrganizationDialogDataBody")
        for organisation_block in organization_list_block.find_all(
                class_="modal-text-block pt-3 pb-3 border-top choiceTableRow"):
            organization = dict()
            address = organisation_block.find(class_="col-3 pl-0 text-break").text.strip()
            if if_correct_address(address, city=city): #TODO: вычление города из адреса и сравнение
                organization['address'] = address
                organization['inn'] = organisation_block.find(class_="col-2 p-0").find("span").text
                organization['name'] = organisation_block.find(
                    class_="not-hierarchical-list__item-label-for-checkbox").text.strip()
                organizations.append(organization)
        print(organizations)
        return organizations

    def parse(self, data_obj: dict) -> list:

        print('---Start parsing---')
        organizations_by_city = []

        num_page = 1
        page_size = 50

        data_obj_name = search_key = data_obj.get("name")
        data_obj_city = data_obj.get("city")

        while True:
            try:
                link_organization_list = f'https://zakupki.gov.ru/epz/organization/chooseOrganization/' \
                                         f'chooseOrganizationTableModal.html?searchString={search_key}' \
                                         f'&inputId=customer&page={num_page}&pageSize={page_size}&organizationType=ALL' \
                                         f'&placeOfSearch=FZ_44,FZ_223&isBm25Search=true'

                soup_by_page_num = self.make_soup(link_organization_list)
                if not soup_by_page_num:
                    break
                organizations_by_city = self.find_organizations_by_city(soup=soup_by_page_num, city=data_obj_city)
                print(f'num_page: {num_page}')
                num_page += 1

            except Exception as e:
                print(e)
                break

        return organizations_by_city

    def get_link_organization_blocks(self, inn: str):
        """
         Getting link on page with lots by inn organization
        """

        print('---Get_link_organization_blocks---')
        link = f'https://zakupki.gov.ru/epz/order/extendedsearch/results.html?searchString={inn}&morphology=on'
        return link

    def get_link_organization_detail(self, link: str):
        """
         Getting detail organization page with contacts
        """

        print('---Get_link_organization_detail---')
        try:
            soup = self.make_soup(url=link)
            contact_link = HOST + soup.find(
                class_='row no-gutters registry-entry__form mr-0'
            ).find(class_='registry-entry__body-href').find('a').get('href')
             # TODO: слияние юрл
            print(f'contact_link: {contact_link}')
            return contact_link
        except AttributeError:
            return None
        except Exception as e:
            print(e)

    def get_contacts_organization(self, contact_link: str, data_obj_name: dict):
        print('---Get_contact_organization---')
        contact = dict()
        contact['Поставщик'] = data_obj_name
        try:
            soup = self.make_soup(contact_link)
            for block_contact in soup.find(class_="blockInfo__title", text='Контактная информация').next.next.next.find_all(class_='blockInfo__section section'):
                feature = block_contact.find(class_="section__title").text.strip()
                if feature in FEATURES:
                    contact[FEATURES.get(feature)] = block_contact.find(class_="section__info").text.strip()

        except Exception as e:
            print(e)

        return contact

    def start(self):
        print('---Start---')
        with open('preparingData.csv', 'r') as preparingDataFile:
            with open('contactData.csv', 'w') as contactDataFile:
                # df = pd.read_csv('data.csv') #TODO: override with no pandas module
                # list_of_column_names = list(df.columns)
                writer = csv.DictWriter(contactDataFile, fieldnames=HEADERS_SHEET)
                reader = csv.DictReader(preparingDataFile, delimiter=',', fieldnames=['name', 'city'])
                try:
                    for num, data_obj in enumerate(reader):
                        if num > 0 : #TODO: ignore table headers
                            organizations = self.parse(data_obj)
                            if organizations:
                                print(f'organizations: {organizations}')
                                for organization in organizations:
                                    link_organization_blocks = self.get_link_organization_blocks(organization.get('inn'))
                                    link_organization_detail = self.get_link_organization_detail(link=link_organization_blocks)
                                    contacts = self.get_contacts_organization(link_organization_detail, data_obj_name=data_obj.get("name"))
                                    print(f'contacts: {contacts}')
                                    writer.writerow(contacts)

                except Exception as e:
                    print(e)


if __name__ == "__main__":
    if not exists('preparingData.csv'):
        preparing_data()

    parser = ContactSpider()
    parser.start()
