import os
import re
import csv
import sys
import json
import datetime
from loguru import logger
from gql import gql, Client
from collections import namedtuple
from gql_query_builder import GqlQuery
from gql.transport.aiohttp import AIOHTTPTransport

class UploadData:
    def __init__(self):
        env = os.environ
        if 'BACKEND_URL' not in env or 'SOURCE_FILE' not in env:
            raise RuntimeError('Missing env values')
        self.__backend = env['BACKEND_URL']
        self.__source = env['SOURCE_FILE']
        transport = AIOHTTPTransport(url=self.__backend)
        self.__api = Client(transport=transport, fetch_schema_from_transport=True)
        self.__start_date = datetime.datetime.now()
        self.__accept_message = 'Accepted by LoadDataFromUOCT Script ({})'.format(self.__start_date)
        logger.info('Using {} as API Endpoint'.format(self.__backend))
        logger.info('Using {} as Data Source'.format(self.__source))
        self.__communes = self.__read_communes()
        self.__companies = self.__read_companies()
        self.__models = self.__read_models()
        self.__full_project = '''
        oid
        metadata {
          status
          commune {
            code
            name
            userInCharge {
              area
              email
              fullName
              role
            }
            maintainer {
              name
            }
          }
          img {
            data
          }
          installationCompany {
            name
          }
          installationDate
          localDetector
          pdfData {
            data
          }
          pedestrianDemand
          pedestrianFacility
          scootDetector
          statusDate
          statusUser {
            fullName
          }
          version
        }
        observation {
          message
        }
        otu {
          junctions {
            jid
            intergreens {
              phfrom
              phto
              value
            }
            sequence {
              phid
              phidSystem
              type
            }
            metadata {
              addressReference
              location {
                coordinates
              }
              useDefaultVi4
            }
            phases
            plans {
              cycle
              plid
              greenStart {
                phid
                value
              }
              pedestrianGreen {
                phid
                value
              }
              phaseStart {
                phid
                value
              }
              systemStart {
                phid
                value
              }
              vehicleGreen {
                phid
                value
              }
              pedestrianIntergreen {
                phfrom
                phto
                value
              }
              vehicleIntergreen {
                phfrom
                phto
                value
              }
            }
          }
          metadata {
            answer
            control
            ipAddress
            linkOwner
            linkType
            netmask
            serial
          }
          programs {
            day
            plan
            time
          }
        }
        controller {
          gps
          model {
            checksum
            company {
              name
            }
            firmwareVersion
            model
          }
        }
        headers {
          hal
          led
          type
        }
        poles {
          hooks
          pedestrian
          vehicular
        }
        ups {
          brand
          capacity
          chargeDuration
          model
          serial
        }'''

    def __read_communes(self):
        q = gql('{ communes { code name } }')
        r = self.__api.execute(q)
        result = {}
        for c in r['communes']:
            result[c['name']] = c['code']
        result['SAN JOAQUIN'] = result['SAN JOAQUÍN']
        result['SANTIAGO'] = result['SANTIAGO CENTRO']
        return result

    def __read_models(self):
        q = gql('{ controllers { company { name } model checksum firmwareVersion } }')
        r = self.__api.execute(q)
        result = set()
        for c in r['controllers']:
            result.add((c['company']['name'].upper(), c['model'].upper(), c['checksum'], c['firmwareVersion']))
        return result

    def __read_companies(self):
        q = gql('{ companies { name } }')
        r = self.__api.execute(q)
        result = set()
        for c in r['companies']:
            result.add(c['name'])
        return result

    def __read_source(self):
        data = []
        with open(self.__source, encoding='utf-8-sig') as fp:
            reader = csv.DictReader(fp, delimiter=';')
            for row in reader:
                data.append(row)
        data_by_jid = {}
        for row in data:
            data_by_jid[row['JID']] = row
        self.__items_by_jid = data_by_jid
        return data

    def __check_new_exists(self, i):
        q = gql("""
            {{
                project(oid: "{}", status: "NEW") {{
                    id
                }}
            }}
        """.format(i['OID']))
        try:
            r = self.__api.execute(q)
            return r['project'] != None
        except Exception:
            return False

    def __accept_new(self, i):
        logger.info('Accepting NEW project oid={}'.format(i['OID']))
        m = gql("""
            mutation {{
                acceptProject(data: {{
                    oid: "{}",
                    status: "NEW",
                    message: "{}"
                }})
            }}
        """.format(i['OID'], self.__accept_message))
        try:
            r = self.__api.execute(m)
        except Exception:
            logger.warning('Failed to accept {}'.format(i['OID']))

    def __read_production(self, oid):
        q = gql("""
            {{
                project(oid: "{}", status: "PRODUCTION") {{
                    {}
                }}
            }}
        """.format(oid, self.__full_project))
        r = self.__api.execute(q)
        if not r['project']:
            logger.warning('Project {} not found in PRODUCTION'.format(oid))
            return None
        return r['project']

    def __create_company(self, name):
        logger.info('Creating new company {}'.format(name))
        q = gql("""
            mutation {{
              createCompany(data: {{
                name: "{}"
              }}) {{
                id
              }}
            }}
        """.format(name))
        try:
            r = self.__api.execute(q)
        except Exception as ex:
            raise RuntimeError('Failed to create company: {} > {}'.format(name, ex))
        self.__companies = self.__read_companies()

    def __create_model(self, model):
        logger.info("Creating new model: {}".format(model))
        q = gql("""
            mutation {{
              createController(data: {{
                company: "{}",
                model: "{}"
              }}) {{
                id
              }}
            }}
        """.format(model['company'], model['model']))
        try:
            r = self.__api.execute(q)
        except Exception as ex:
            raise RuntimeError('Failed to create model: {} > {}'.format(model, ex))
        self.__models = self.__read_models()

    def __update_project(self, proj, item):
        logger.info("Updating project {}".format(proj['oid']))
        item['COMMUNE'] = item['COMMUNE'].upper()
        if item['COMMUNE'] not in self.__communes:
            logger.warning('Missing {} in backend communes, leaving as default'.format(item['COMMUNE']))
            proj['metadata']['commune'] = self.__communes['SIN ASIGNAR']
        else:
            proj['metadata']['commune'] = self.__communes[item['COMMUNE']]
        for junc in proj['otu']['junctions']:
            if junc['jid'] not in self.__items_by_jid:
                logger.warning('Missing jid={} in __items_by_jid dict'.format(junc['jid']))
                return None
            junc_item = self.__items_by_jid[junc['jid']]
            new_coords = [float(junc_item['LAT'].replace(',', '.')), float(junc_item['LON'].replace(',', '.'))] 
            ref = '{} - {}'.format(junc_item['STREET 1'], junc_item['STREET 2'])
            del junc['metadata']['location']
            junc['metadata']['coordinates'] = new_coords
            junc['metadata']['addressReference'] = ref
            for p in junc['plans']:
                for i in p['pedestrianIntergreen']:
                    i['phfrom'] = str(i['phfrom'])
                    i['phto'] = str(i['phto'])
                    i['value'] = str(i['value'])
                for i in p['vehicleIntergreen']:
                    i['phfrom'] = str(i['phfrom'])
                    i['phto'] = str(i['phto'])
                    i['value'] = str(i['value'])
            logger.debug('Assigned location {} and reference "{}" to {}'.format(new_coords, ref, junc['jid']))
        item['MAINTAINER_NAME'] = item['MAINTAINER_NAME'].upper()
        item['MODEL_COMPANY'] = item['MODEL_COMPANY'].upper()
        item['MODEL_NAME'] = item['MODEL_NAME'].upper()
        if item['MODEL_COMPANY'] == '':
            item['MODEL_COMPANY'] = 'SPEEDEVS'
        if item['MAINTAINER_NAME'] == '':
            item['MAINTAINER_NAME'] = 'SPEEDEVS'
        if item['MAINTAINER_NAME'] not in self.__companies:
            self.__create_company(item['MAINTAINER_NAME'])
        if item['MODEL_COMPANY'] not in self.__companies:
            self.__create_company(item['MODEL_COMPANY'])
        new_model = {
            'company': item['MODEL_COMPANY'],
            'model': item['MODEL_NAME'],
        }
        if (new_model['company'], new_model['model'], 'Missing Value', 'Missing Value')  not in self.__models:
            self.__create_model(new_model)
        proj['controller']['model'] = new_model

        del proj['metadata']['status']
        del proj['metadata']['img']
        del proj['metadata']['pdfData']
        del proj['metadata']['statusDate']
        del proj['metadata']['statusUser']
        del proj['metadata']['version']

        proj['observation'] = proj['observation']['message']
        proj['status'] = 'UPDATE'
        proj['controller']['model']['firmwareVersion'] = 'Missing Value'
        proj['controller']['model']['checksum'] = 'Missing Value'

        return proj

    def __send_update(self, proj):
        logger.debug('Sending UPDATE for {} to backend'.format(proj['oid']))
        q = gql('''
            mutation {{
                updateProject(data: {})
            }}
        '''.format(self.__dict_to_graphql(proj)))
        r = self.__api.execute(q)
        return r['updateProject']

    def __accept_update(self, oid):
        logger.info('Accepting UPDATE project oid={}'.format(oid))
        m = gql("""
            mutation {{
                acceptProject(data: {{
                    oid: "{}",
                    status: "UPDATE",
                    message: "{}"
                }})
            }}
        """.format(oid, self.__accept_message))
        try:
            r = self.__api.execute(m)
        except Exception:
            logger.warning('Failed to accept {}'.format(oid))

    def __upload_item(self, i):
        logger.info('Processing item for {}'.format(i['OID']))
        proj = self.__read_production(i['OID'])
        if proj:
            updated = self.__update_project(proj, i)
            if updated:
                uid = self.__send_update(updated)
                logger.debug('Created UPDATE event with id={}'.format(uid))
                self.__accept_update(updated['oid'])
                logger.info('Done for project {}'.format(i['OID']))

    def run(self):
        data = self.__read_source()
        logger.debug('We have {} entries to upload'.format(len(data)))
        for idx, item in enumerate(data):
            if self.__check_new_exists(item):
                self.__accept_new(item)
            self.__upload_item(item)
            logger.debug('Uploaded {} of {}'.format(idx + 1, len(data)))

    def __dict_to_graphql(self, data, depth=0):
        s = json.dumps(self.__clean_dict(data), indent=4)
        return re.sub(r'"(.+)":\s', r'\1: ', s)

    def __clean_dict(self, data):
        for k, v in list(data.items()):
            if v is None:
                del data[k]
            elif isinstance(v, dict):
                self.__clean_dict(v)
        return data

if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level='DEBUG')
    try:
        logger.info('Starting')
        remover = UploadData()
        remover.run()
        logger.info('Done')
    except Exception as excep:
        logger.exception('Global Exception!')
