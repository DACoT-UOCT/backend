import os
import json
import base64
import mongomock
import mongomock.gridfs
from graphene.test import Client as GQLClient

os.environ["authjwt_secret_key"] = "JCTn;o1?wH:c<aJJt;HO4wXQW}*Rz("
os.environ["mongo_db"] = "db"
os.environ["mongo_uri"] = "mongomock://127.0.0.1"
os.environ["RUNNING_TEST"] = "OK"

import unittest
from fastapi_backend.app import main as production_main
from fastapi_backend.app.graphql_schema import dacot_schema
from fastapi.testclient import TestClient
from deploy.seed_db_module import seed_from_interpreter, drop_old_data

TEST_USER_FULLNAME = "Test User Full Name"


def reset_db_state():
    seed_from_interpreter(
        os.environ.get("mongo_uri"),
        os.environ.get("mongo_db"),
        "tests/cmodels.csv",
        "tests/juncs.csv",
        "tests/scheds.json",
        "tests/communes_reg_metrop.json",
    )


class TestFastAPI(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestFastAPI, self).__init__(*args, **kwargs)
        self.client = TestClient(production_main.app)
        self.gql = GQLClient(schema=dacot_schema)
        mongomock.gridfs.enable_gridfs_integration()

    @classmethod
    def setUpClass(cls):
        reset_db_state()

    def setUp(self):
        reset_db_state()

    def assert_errors_and_get_messages(self, mutation_result):
        assert "errors" in mutation_result
        assert len(mutation_result["errors"]) > 0
        err_messages = str([err["message"] for err in mutation_result["errors"]])
        return err_messages

    def parse_mongomock_id(self, mock_id):
        return str(base64.b64decode(mock_id)).replace("'", "").split(":")[1]

    def test_auth_do_login_apikey(self):
        self.skipTest("Not Completed")
        data = {"query": '{ loginApiKey(key: "key", secret: "secret_key") }'}
        response = self.client.post("/graphql", json=data)
        response.raise_for_status()

    def test_gql_get_users(self):
        result = self.gql.execute("query { users { email fullName } }")
        emails = [u["email"] for u in result["data"]["users"]]
        assert "admin@dacot.uoct.cl" in emails
        assert "seed@dacot.uoct.cl" in emails

    def test_gql_get_users_single_user(self):
        result = self.gql.execute(
            'query { user(email: "admin@dacot.uoct.cl") { email fullName } }'
        )
        assert result["data"]["user"]["fullName"] == "Admin"

    def test_gql_get_users_single_user_and_company(self):
        result = self.gql.execute(
            'query { user(email: "employee@acmecorp.com") { email fullName company { name } } }'
        )
        assert result["data"]["user"]["email"] == "employee@acmecorp.com"
        assert result["data"]["user"]["company"]["name"] == "ACME Corporation"

    def test_gql_get_users_single_user_not_exists(self):
        result = self.gql.execute(
            'query { user(email: "notfound@example.com") { email fullName } }'
        )
        assert result["data"]["user"] == None

    def test_gql_get_users_empty_list(self):
        drop_old_data()
        result = self.gql.execute("query { users { email fullName } }")
        assert type(result["data"]["users"]) == list
        assert len(result["data"]["users"]) == 0

    def test_gql_get_users_attribute_not_exists(self):
        result = self.gql.execute(
            "query { users { email fullName attribute_not_exists } }"
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Cannot query field 'attribute_not_exists' on type 'User'." in err_messages
        )

    def test_gql_get_users_invalid_query(self):
        result = self.gql.execute("query { {{{ users { email fullName } }")
        err_messages = self.assert_errors_and_get_messages(result)
        assert "Syntax Error" in err_messages

    def test_gql_create_user(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        assert result["data"]["createUser"]["email"] == "user@example.org"
        assert result["data"]["createUser"]["fullName"] == TEST_USER_FULLNAME
        assert result["data"]["createUser"]["id"] != None
        result = self.gql.execute(
            'query { user(email: "user@example.org") { fullName } }'
        )
        assert result["data"]["user"]["fullName"] == TEST_USER_FULLNAME

    def test_gql_create_user_is_admin(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: true,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName isAdmin
            }
        }
        """
        )
        assert result["data"]["createUser"]["email"] == "user@example.org"
        assert result["data"]["createUser"]["fullName"] == TEST_USER_FULLNAME
        assert result["data"]["createUser"]["id"] != None
        assert result["data"]["createUser"]["isAdmin"] == True
        result = self.gql.execute(
            'query { user(email: "user@example.org") { isAdmin fullName } }'
        )
        assert result["data"]["user"]["fullName"] == TEST_USER_FULLNAME
        assert result["data"]["user"]["isAdmin"] == True

    def test_gql_create_user_invalid_full_name(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: true,
                fullName: "A",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "String value is too short: ['full_name']" in err_messages

    def test_gql_create_user_invalid_email(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example@google@cl.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "Invalid email address: user@example@google@cl.org" in err_messages

    def test_gql_create_user_invalid_role(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Invalid_ROLE",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "Value must be one of" in err_messages
        assert "['role']" in err_messages

    def test_gql_create_user_invalid_area(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Invalid_AREA"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "Value must be one of" in err_messages
        assert "['area']" in err_messages

    def test_gql_create_user_missing_attribute(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName isAdmin
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'CreateUserInput.isAdmin' of required type 'Boolean!' was not provided."
            in err_messages
        )

    def test_gql_create_user_duplicated(self):
        self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "E11000 Duplicate Key Error" in err_messages

    def test_gql_create_user_company(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora",
                company: "ACME Corporation"
            })
            {
                id email fullName company { id name }
            }
        }
        """
        )
        assert not "errors" in result
        assert result["data"]["createUser"]["id"] != None
        assert result["data"]["createUser"]["company"]["name"] == "ACME Corporation"
        assert result["data"]["createUser"]["company"]["id"] != None

    def test_gql_create_user_company_not_found(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora",
                company: "Fake Company"
            })
            {
                id email fullName
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'ExternalCompany "Fake Company" not found' in err_messages

    def test_gql_create_user_uoct_role(self):
        result = self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Personal UOCT",
                area: "TIC"
            })
            {
                id email fullName isAdmin
            }
        }
        """
        )
        assert not "errors" in result
        assert result["data"]["createUser"]["email"] == "user@example.org"
        assert result["data"]["createUser"]["fullName"] == TEST_USER_FULLNAME
        assert result["data"]["createUser"]["id"] != None
        assert result["data"]["createUser"]["isAdmin"] == False

    def test_gql_delete_user(self):
        result = self.gql.execute(
            """
        mutation {
            deleteUser(userDetails: {
                email: "employee@acmecorp.com"
            })
        }
        """
        )
        assert not "errors" in result
        assert result["data"]["deleteUser"] != None

    def test_gql_delete_user_not_exists(self):
        result = self.gql.execute(
            """
        mutation {
            deleteUser(userDetails: {
                email: "user_not_found@example.org"
            })
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'User "user_not_found@example.org" not found' in err_messages

    def test_gql_update_user_admin(self):
        result = self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "employee@acmecorp.com",
                isAdmin: true
            })
            {
                id isAdmin email
            }
        }
        """
        )
        assert not "errors" in result
        assert result["data"]["updateUser"]["email"] == "employee@acmecorp.com"
        assert result["data"]["updateUser"]["id"] != None
        assert result["data"]["updateUser"]["isAdmin"] == True

    def test_gql_update_user_full_name(self):
        result = self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "employee@acmecorp.com",
                fullName: "Updated Full Name Value"
            })
            {
                id fullName email
            }
        }
        """
        )
        assert not "errors" in result
        assert result["data"]["updateUser"]["email"] == "employee@acmecorp.com"
        assert result["data"]["updateUser"]["id"] != None
        assert result["data"]["updateUser"]["fullName"] == "Updated Full Name Value"

    def test_gql_update_user_not_found(self):
        result = self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "user_not_found@example.org"
            })
            {
                id
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'User "user_not_found@example.org" not found' in err_messages

    def test_gql_update_user_invalid_field(self):
        result = self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "user_not_found@example.org",
                company: "Updated Company Value"
            })
            {
                id
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'company' is not defined by type 'UpdateUserInput'." in err_messages
        )

    def test_gql_actions_log_get_all_empty(self):
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) == 0

    def test_gql_actions_log_get_all_create_user(self):
        self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "Mantenedora"
            })
            {
                id email fullName
            }
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'User "user@example.org" created'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_all_create_user_failed(self):
        self.gql.execute(
            """
        mutation {
            createUser(userDetails: {
                isAdmin: false,
                fullName: "Test User Full Name",
                email: "user@example.org",
                role: "Empresa",
                area: "INVALID"
            })
            {
                id email fullName
            }
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'Failed to create user "user@example.org"'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_all_delete_user(self):
        self.gql.execute(
            """
        mutation {
            deleteUser(userDetails: {
                email: "employee@acmecorp.com"
            })
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'User "employee@acmecorp.com" deleted'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_all_delete_user_failed(self):
        self.gql.execute(
            """
        mutation {
            deleteUser(userDetails: {
                email: "user_not_found@example.org"
            })
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'Failed to delete user "user_not_found@example.org"'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_all_update_user(self):
        self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "employee@acmecorp.com",
                isAdmin: true
            })
            {
                id
            }
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { id action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'User "employee@acmecorp.com" updated'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_all_update_user_not_found(self):
        self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "user_not_found@example.org",
                isAdmin: false
            })
            {
                id
            }
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert (
            'Failed to update user "user_not_found@example.org"'
            in result["data"]["actionsLogs"][0]["action"]
        )

    def test_gql_actions_log_get_single(self):
        self.gql.execute(
            """
        mutation {
            updateUser(userDetails: {
                email: "employee@acmecorp.com",
                isAdmin: true
            })
            {
                id
            }
        }
        """
        )
        result = self.gql.execute("query { actionsLogs { id action } }")
        assert "errors" not in result
        assert len(result["data"]["actionsLogs"]) > 0
        assert result["data"]["actionsLogs"][0]["id"] != None
        logid = result["data"]["actionsLogs"][0]["id"]
        qry = 'query {{ actionsLog(logid: "{}") {{ id user context action date }} }}'.format(
            logid
        )
        result = self.gql.execute(qry)
        assert "errors" not in result
        assert (
            'User "employee@acmecorp.com" updated.'
            in result["data"]["actionsLog"]["action"]
        )

    def test_gql_get_communes(self):
        result = self.gql.execute(
            "query { communes { code name maintainer { name } userInCharge { email } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["communes"]) > 0

    def test_gql_get_communes_empty(self):
        drop_old_data()
        result = self.gql.execute(
            "query { communes { code name maintainer { name } userInCharge { email } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["communes"]) == 0

    def test_gql_update_commune_not_found(self):
        result = self.gql.execute(
            """
        mutation {
            updateCommune(communeDetails: {
                code: 1,
                userInCharge: "employee@acmecorp.com"
            })
            {
                code userInCharge { email }
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'Commune "1" not found' in err_messages

    def test_gql_update_commune_maintainer(self):
        result = self.gql.execute(
            """
        mutation {
            updateCommune(communeDetails: {
                code: 13108,
                maintainer: "ACME Corporation"
            })
            {
                code maintainer { name }
            }
        }
        """
        )
        assert "errors" not in result
        assert result["data"]["updateCommune"]["code"] == 13108
        assert (
            result["data"]["updateCommune"]["maintainer"]["name"] == "ACME Corporation"
        )

    def test_gql_update_commune_user(self):
        result = self.gql.execute(
            """
        mutation {
            updateCommune(communeDetails: {
                code: 13108,
                userInCharge: "employee@acmecorp.com"
            })
            {
                code userInCharge { email }
            }
        }
        """
        )
        assert "errors" not in result
        assert result["data"]["updateCommune"]["code"] == 13108
        assert (
            result["data"]["updateCommune"]["userInCharge"]["email"]
            == "employee@acmecorp.com"
        )

    def test_gql_update_commune_invalid_field(self):
        result = self.gql.execute(
            """
        mutation {
            updateCommune(communeDetails: {
                code: 13108,
                name: "Valparaíso"
            })
            {
                code name
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'name' is not defined by type 'UpdateCommuneInput'." in err_messages
        )

    def test_gql_get_companies(self):
        result = self.gql.execute("query { companies { name } }")
        assert "errors" not in result
        assert len(result["data"]["companies"]) > 0
        names = [x["name"] for x in result["data"]["companies"]]
        assert "ACME Corporation" in names

    def test_gql_get_companies_empty(self):
        drop_old_data()
        result = self.gql.execute("query { companies { name } }")
        assert "errors" not in result
        assert len(result["data"]["companies"]) == 0

    def test_gql_create_company(self):
        result = self.gql.execute(
            """
        mutation {
            createCompany(companyDetails: {
                name: "SpeeDevs"
            })
            {
                name
            }
        }
        """
        )
        assert "errors" not in result
        assert result["data"]["createCompany"]["name"] == "SpeeDevs"

    def test_gql_create_company_invalid_name(self):
        result = self.gql.execute(
            """
        mutation {
            createCompany(companyDetails: {
                name: "A"
            })
            {
                name
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "String value is too short" in err_messages

    def test_gql_create_company_invalid_field(self):
        result = self.gql.execute(
            """
        mutation {
            createCompany(companyDetails: {
                nameOfTheNewCompany: "A"
            })
            {
                name
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "Field 'nameOfTheNewCompany' is not defined" in err_messages

    def test_gql_create_company_missing_field(self):
        result = self.gql.execute(
            """
        mutation {
            createCompany(companyDetails: {})
            {
                name
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'CreateCompanyInput.name' of required type 'String!' was not provided."
            in err_messages
        )

    def test_gql_create_company_duplicated(self):
        result = self.gql.execute(
            """
        mutation {
            createCompany(companyDetails: {
                name: "ACME Corporation"
            })
            {
                name
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "E11000 Duplicate Key Error" in err_messages

    def test_gql_delete_company(self):
        result = self.gql.execute(
            """
        mutation {
            deleteCompany(companyDetails: {
                name: "ACME Corporation"
            })
        }
        """
        )
        assert "errors" not in result

    def test_gql_delete_company_not_found(self):
        result = self.gql.execute(
            """
        mutation {
            deleteCompany(companyDetails: {
                name: "Fake Company"
            })
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'Company "Fake Company" not found' in err_messages

    def test_gql_get_junctions_coordinates(self):
        result = self.gql.execute(
            "query { junctions { jid metadata { location { coordinates } } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["junctions"]) > 0

    def test_gql_get_junctions_coordinates_empty(self):
        drop_old_data()
        result = self.gql.execute(
            "query { junctions { jid metadata { location { coordinates } } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["junctions"]) == 0

    def test_gql_create_failed_plan(self):
        result = self.gql.execute(
            """
        mutation {
            createFailedPlan(messageDetails: {
                message: "Test Message",
                plans: [
                    "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   2 AAAAAAA M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   3 J001123 CY104 C* 30, A* 46, B* 97"
                ]
            })
            {
                id date comment { author { fullName email } message } plans
            }
        }
        """
        )
        assert "errors" not in result
        assert (
            result["data"]["createFailedPlan"]["comment"]["message"] == "Test Message"
        )
        assert len(result["data"]["createFailedPlan"]["plans"])

    def test_gql_create_failed_plan_invalid(self):
        result = self.gql.execute(
            """
        mutation {
            createFailedPlan(messageDetails: {
                message: "Test Message",
                plans: []
            })
            {
                id date comment { author { fullName email } message } plans
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "ValidationError" in err_messages
        assert "Field is required and cannot be empty" in err_messages

    def test_gql_get_failed_plans(self):
        self.gql.execute(
            """
        mutation {
            createFailedPlan(messageDetails: {
                message: "Test Message",
                plans: [
                    "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   2 AAAAAAA M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   3 J001123 CY104 C* 30, A* 46, B* 97"
                ]
            })
            {
                id
            }
        }
        """
        )
        result = self.gql.execute(
            "query { failedPlans { id date comment { message } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["failedPlans"]) > 0

    def test_gql_get_failed_plans_empty(self):
        result = self.gql.execute(
            "query { failedPlans { id date comment { message } } }"
        )
        assert "errors" not in result
        assert len(result["data"]["failedPlans"]) == 0

    def test_gql_get_single_failed_plan(self):
        mid = self.gql.execute(
            """
        mutation {
            createFailedPlan(messageDetails: {
                message: "Test Message",
                plans: [
                    "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   2 AAAAAAA M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   3 J001123 CY104 C* 30, A* 46, B* 97"
                ]
            })
            {
                id
            }
        }
        """
        )["data"]["createFailedPlan"]["id"]
        result = self.gql.execute(
            'query {{ failedPlan(mid: "{}") {{ id date comment {{ message }} }} }}'.format(
                mid
            )
        )
        assert "errors" not in result
        assert result["data"]["failedPlan"]["id"] == mid

    def test_gql_get_single_failed_plan_not_found(self):
        fake_mid = "00000a1bdacc63d2cd111111"
        result = self.gql.execute(
            'query {{ failedPlan(mid: "{}") {{ id date comment {{ message }} }} }}'.format(
                fake_mid
            )
        )
        assert "errors" not in result
        assert result["data"]["failedPlan"] == None

    def test_gql_delete_single_failed_plan(self):
        mid = self.gql.execute(
            """
        mutation {
            createFailedPlan(messageDetails: {
                message: "Test Message",
                plans: [
                    "Plan   1 J001121 M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   2 AAAAAAA M.MONTT-PROVIDE CY104 C 30, A 46, B 97",
                    "Plan   3 J001123 CY104 C* 30, A* 46, B* 97"
                ]
            })
            {
                id
            }
        }
        """
        )["data"]["createFailedPlan"]["id"]
        result = self.gql.execute(
            """
        mutation {{
            deleteFailedPlan(messageDetails: {{
                mid: "{}"
            }})
        }}
        """.format(
                mid
            )
        )
        assert "errors" not in result
        assert result["data"]["deleteFailedPlan"] == mid

    def test_gql_get_controller_models(self):
        result = self.gql.execute(
            "query { controllerModels { company { name } model date } }"
        )
        assert "errors" not in result
        assert len(result["data"]["controllerModels"]) > 0

    def test_gql_get_controller_models_empty(self):
        drop_old_data()
        result = self.gql.execute(
            "query { controllerModels { company { name } model date } }"
        )
        assert "errors" not in result
        assert len(result["data"]["controllerModels"]) == 0

    def test_gql_create_controller_model(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
                firmwareVersion: "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux",
                checksum: "TGludXggNC4xOS4xMDQgeDg2XzY0"
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        assert "errors" not in result
        assert (
            result["data"]["createController"]["company"]["name"] == "ACME Corporation"
        )
        assert result["data"]["createController"]["model"] == "ABC1"
        assert (
            result["data"]["createController"]["firmwareVersion"]
            == "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux"
        )
        assert (
            result["data"]["createController"]["checksum"]
            == "TGludXggNC4xOS4xMDQgeDg2XzY0"
        )

    def test_gql_create_controller_model_company_not_found(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME",
                model: "ABC1",
                firmwareVersion: "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux",
                checksum: "TGludXggNC4xOS4xMDQgeDg2XzY0"
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'Company "ACME" not found' in err_messages

    def test_gql_create_controller_model_missing_field(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                model: "ABC1",
                firmwareVersion: "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux",
                checksum: "TGludXggNC4xOS4xMDQgeDg2XzY0"
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'CreateControllerModelInput.company' of required type 'String!' was not provided."
            in err_messages
        )

    def test_gql_create_controller_model_invalid_field(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                modelField: "ABC1",
                firmwareVersion: "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux",
                checksum: "TGludXggNC4xOS4xMDQgeDg2XzY0"
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'modelField' is not defined by type 'CreateControllerModelInput'"
            in err_messages
        )

    def test_gql_create_controller_model_with_firmware(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
                firmwareVersion: "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        assert "errors" not in result
        assert (
            result["data"]["createController"]["company"]["name"] == "ACME Corporation"
        )
        assert result["data"]["createController"]["model"] == "ABC1"
        assert (
            result["data"]["createController"]["firmwareVersion"]
            == "Linux 4.19.104-microsoft-standard x86_64 GNU/Linux"
        )
        assert result["data"]["createController"]["checksum"] == "Missing Value"

    def test_gql_create_controller_model_with_version(self):
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
                checksum: "TGludXggNC4xOS4xMDQgeDg2XzY0"
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        assert "errors" not in result
        assert (
            result["data"]["createController"]["company"]["name"] == "ACME Corporation"
        )
        assert result["data"]["createController"]["model"] == "ABC1"
        assert result["data"]["createController"]["firmwareVersion"] == "Missing Value"
        assert (
            result["data"]["createController"]["checksum"]
            == "TGludXggNC4xOS4xMDQgeDg2XzY0"
        )

    def test_gql_create_controller_model_duplicated(self):
        self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        result = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "E11000 Duplicate Key Error" in err_messages

    def test_gql_update_controller_model(self):
        cid = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )["data"]["createController"]["id"]
        result = self.gql.execute(
            """
        mutation {{
            updateController(controllerDetails: {{
                cid: "{}",
                firmwareVersion: "Firmware1",
                checksum: "ChecksumValue"
            }})
            {{
                id company {{ name }} model firmwareVersion checksum
            }}
        }}
        """.format(
                cid
            )
        )
        assert "errors" not in result
        assert result["data"]["updateController"]["firmwareVersion"] == "Firmware1"
        assert result["data"]["updateController"]["checksum"] == "ChecksumValue"

    def test_gql_update_controller_model_not_found(self):
        fake_cid = "00000a1bdacc63d2cd111111"
        result = self.gql.execute(
            """
        mutation {{
            updateController(controllerDetails: {{
                cid: "{}",
                firmwareVersion: "Firmware1",
                checksum: "ChecksumValue"
            }})
            {{
                id company {{ name }} model firmwareVersion checksum
            }}
        }}
        """.format(
                fake_cid
            )
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'Model "00000a1bdacc63d2cd111111" not found' in err_messages

    def test_gql_update_controller_model_invalid_field(self):
        cid = self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )["data"]["createController"]["id"]
        result = self.gql.execute(
            """
        mutation {{
            updateController(controllerDetails: {{
                cid: "{}",
                company: "ACME",
                firmwareVersion: "Firmware1",
                checksum: "ChecksumValue"
            }})
            {{
                id company {{ name }} model firmwareVersion checksum
            }}
        }}
        """.format(
                cid
            )
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'company' is not defined by type 'UpdateControllerModelInput'."
            in err_messages
        )

    def test_gql_get_otus_all(self):
        result = self.gql.execute(
            """
        query {
            otus {
                oid metadata {
                    serial ipAddress netmask
                } programs {
                    day time plan
                } sequences {
                    seqid phases {
                        phid stages {
                            stid type
                        }
                    }
                } intergreens junctions {
                    jid metadata {
                        location {
                            coordinates
                        } salesId addressReference
                    } plans {
                        plid cycle phaseStart { phid value } vehicleIntergreen { phfrom phto value }
                        greenStart { phid value } vehicleGreen { phid value } pedestrianGreen { phid value }
                        pedestrianIntergreen { phfrom phto value } systemStart { phid value }
                    }
                }
            }
        }
        """
        )
        assert "errors" not in result
        assert len(result["data"]["otus"]) > 0

    def test_gql_get_otus_all_empty(self):
        drop_old_data()
        result = self.gql.execute("query { otus { oid } }")
        assert "errors" not in result
        assert len(result["data"]["otus"]) == 0

    def test_gql_get_single_otu(self):
        result = self.gql.execute('query { otu(oid: "X001140") { oid } }')
        assert "errors" not in result
        assert result["data"]["otu"]["oid"] == "X001140"

    def test_gql_get_single_otu_not_found(self):
        result = self.gql.execute('query { otu(oid: "AAAAA") { oid } }')
        assert "errors" not in result
        assert result["data"]["otu"] == None

    def test_gql_get_single_otu_invalid_field(self):
        result = self.gql.execute('query { otu(oid: "X001140") { invalidField } }')
        err_messages = self.assert_errors_and_get_messages(result)
        assert "Cannot query field 'invalidField' on type 'OTU'." in err_messages

    def test_gql_create_project(self):
        self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        result = self.gql.execute(
            """
            mutation {
                createProject(projectDetails: {
                        oid: "X001110",
                        metadata: {
                            maintainer: "ACME Corporation",
                            commune: 13106
                        },
                        controller: {
                            addressReference: "Street #Number",
                            gps: false,
                            model: {
                                company: "ACME Corporation",
                                model: "ABC1",
                                firmwareVersion: "Missing Value",
                                checksum: "Missing Value"
                            }
                        },
                        otu: {
                            junctions: [
                                {
                                    jid: "J001111",
                                    metadata: {
                                        coordinates: [10.10, 20.20],
                                        addressReference: "Street #Number1"
                                    }
                                },
                                {
                                    jid: "J001112",
                                    metadata: {
                                        coordinates: [30.30, 40.50],
                                        addressReference: "Street #Number2"
                                    }
                                }
                            ]
                        },
                        observation: "Created from selftest"
                    }
                ) { oid }
            }
        """
        )
        assert not "errors" in result
        assert result["data"]["createProject"]["oid"] == "X001110"

    def test_gql_update_project_create(self):
        self.gql.execute(
            """
        mutation {
            createController(controllerDetails: {
                company: "ACME Corporation",
                model: "ABC1",
            })
            {
                id company { name } model firmwareVersion checksum
            }
        }
        """
        )
        result = self.gql.execute(
            """
            mutation {
                updateProject(projectDetails: {
                        oid: "X001110",
                        metadata: {
                            maintainer: "ACME Corporation",
                            commune: 13106
                        },
                        controller: {
                            addressReference: "Street #Number",
                            gps: false,
                            model: {
                                company: "ACME Corporation",
                                model: "ABC1",
                                firmwareVersion: "Missing Value",
                                checksum: "Missing Value"
                            }
                        },
                        otu: {
                            junctions: [
                                {
                                    jid: "J001111",
                                    metadata: {
                                        coordinates: [10.10, 20.20],
                                        addressReference: "Street #Number1"
                                    }
                                },
                                {
                                    jid: "J001112",
                                    metadata: {
                                        coordinates: [30.30, 40.50],
                                        addressReference: "Street #Number2"
                                    }
                                }
                            ]
                        },
                        observation: "Created from selftest"
                    }
                ) { oid }
            }
        """
        )
        assert not "errors" in result
        assert result["data"]["updateProject"]["oid"] == "X001110"

    def test_gql_update_project_accept(self):
        self.test_gql_update_project_create()
        result = self.gql.execute(
            'mutation { acceptProject(projectDetails: { oid: "X001110" status: "UPDATE"}) }'
        )
        assert not "errors" in result
        assert result["data"]["acceptProject"] == "X001110"

    def test_gql_get_all_projects(self):
        result = self.gql.execute("query { allProjects { oid metadata { status } } }")
        assert not "errors" in result
        assert len(result["data"]["allProjects"])

    def test_gql_get_update_projects_empty(self):
        result = self.gql.execute(
            'query { projects(status: "UPDATE") { oid metadata { status } } }'
        )
        assert not "errors" in result
        assert len(result["data"]["projects"]) == 0

    def test_gql_get_update_projects_create_and_accept(self):
        self.test_gql_get_update_projects_empty()
        self.test_gql_update_project_create()
        result1 = self.gql.execute(
            'query { projects(status: "UPDATE") { oid metadata { status } } }'
        )
        assert not "errors" in result1
        assert len(result1["data"]["projects"]) == 1
        self.gql.execute(
            'mutation { acceptProject(projectDetails: { oid: "X001110" status: "UPDATE"}) }'
        )
        self.test_gql_get_update_projects_empty()

    def test_gql_get_update_projects_create_and_delete(self):
        self.test_gql_get_update_projects_empty()
        self.test_gql_update_project_create()
        result1 = self.gql.execute(
            'query { projects(status: "UPDATE") { oid metadata { status } } }'
        )
        assert not "errors" in result1
        assert len(result1["data"]["projects"]) == 1
        response = self.gql.execute(
            'mutation { deleteProject(projectDetails: { oid: "X001110" status: "UPDATE"}) }'
        )
        assert not "errors" in response
        self.test_gql_get_update_projects_empty()

    def test_gql_get_update_projects_create_and_reject(self):
        self.test_gql_get_update_projects_empty()
        self.test_gql_update_project_create()
        result1 = self.gql.execute(
            'query { projects(status: "UPDATE") { oid metadata { status } } }'
        )
        assert not "errors" in result1
        assert len(result1["data"]["projects"]) == 1
        response = self.gql.execute(
            'mutation { rejectProject(projectDetails: { oid: "X001110" status: "UPDATE"}) }'
        )
        assert not "errors" in response
        self.test_gql_get_update_projects_empty()

    def test_gql_list_versions_create_and_accept_update(self):
        self.test_gql_list_versions_empty()
        self.test_gql_get_update_projects_create_and_accept()
        result = self.gql.execute(
            'query { versions(oid: "X001110") { vid date comment { author { email } message } } }'
        )
        assert not "errors" in result
        assert (
            len(result["data"]["versions"]) == 3
        )  # TODO: FIXME: This will break when updating seed script (drop base version)

    def test_gql_list_versions_empty(self):
        result = self.gql.execute(
            'query { versions(oid: "X001110") { vid date comment { author { email } message } } }'
        )
        assert not "errors" in result
        assert (
            len(result["data"]["versions"]) == 2
        )  # TODO: FIXME: This will break when updating seed script (drop base version)

    def test_gql_get_single_version(self):
        result = self.gql.execute(
            'query { version(oid: "X001110", vid: "latest") { oid metadata { status version } } }'
        )
        assert not "errors" in result
        assert result["data"]["version"]["oid"] == "X001110"
        assert result["data"]["version"]["metadata"]["status"] == "PRODUCTION"
        assert result["data"]["version"]["metadata"]["version"] == "latest"

    def test_gql_check_otu_exists(self):
        result = self.gql.execute('query { checkOtuExists(oid: "X001110") }')
        assert not "errors" in result
        assert result["data"]["checkOtuExists"] == True

    def test_gql_check_otu_exists_not_found(self):
        result = self.gql.execute('query { checkOtuExists(oid: "X001111") }')
        assert not "errors" in result
        assert result["data"]["checkOtuExists"] == False

    def test_gql_check_otu_exists_invalid_input(self):
        result = self.gql.execute('query { checkOtuExists(inputValue: "X001111") }')
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Unknown argument 'inputValue' on field 'Query.checkOtuExists'."
            in err_messages
        )

    def test_gql_check_otu_exists_null_input(self):
        result = self.gql.execute('query { checkOtuExists(oid: "") }')
        assert not "errors" in result
        assert result["data"]["checkOtuExists"] == False

    def test_gql_create_commune_min_fields(self):
        result = self.gql.execute(
            'mutation { createCommune(communeDetails: { code: 10101, name: "FakeName" }) { name code } }'
        )
        assert not "errors" in result
        assert result["data"]["createCommune"]["code"] == 10101
        assert result["data"]["createCommune"]["name"] == "FakeName"

    def test_gql_create_commune_all_fields(self):
        result = self.gql.execute(
            """mutation {
            createCommune(communeDetails: {
                code: 10101, name: "FakeName", maintainer: "ACME Corporation", userInCharge: "seed@dacot.uoct.cl"
                }
            ) { name code maintainer { name } userInCharge { email } }
        }"""
        )
        assert not "errors" in result
        assert result["data"]["createCommune"]["code"] == 10101
        assert result["data"]["createCommune"]["name"] == "FakeName"
        assert (
            result["data"]["createCommune"]["maintainer"]["name"] == "ACME Corporation"
        )
        assert (
            result["data"]["createCommune"]["userInCharge"]["email"]
            == "seed@dacot.uoct.cl"
        )

    def test_gql_create_commune_only_user(self):
        result = self.gql.execute(
            """mutation {
            createCommune(communeDetails: {
                code: 10101, name: "FakeName", userInCharge: "seed@dacot.uoct.cl"
                }
            ) { name code maintainer { name } userInCharge { email } }
        }"""
        )
        assert not "errors" in result
        assert result["data"]["createCommune"]["code"] == 10101
        assert result["data"]["createCommune"]["name"] == "FakeName"
        assert (
            result["data"]["createCommune"]["userInCharge"]["email"]
            == "seed@dacot.uoct.cl"
        )

    def test_gql_create_commune_only_maintainer(self):
        result = self.gql.execute(
            """mutation {
            createCommune(communeDetails: {
                code: 10101, name: "FakeName", maintainer: "ACME Corporation"
                }
            ) { name code maintainer { name } userInCharge { email } }
        }"""
        )
        assert not "errors" in result
        assert result["data"]["createCommune"]["code"] == 10101
        assert result["data"]["createCommune"]["name"] == "FakeName"
        assert (
            result["data"]["createCommune"]["maintainer"]["name"] == "ACME Corporation"
        )

    def test_gql_create_commune_missing_fields(self):
        result = self.gql.execute(
            "mutation { createCommune(communeDetails: { code: 10101 }) { name code } }"
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Field 'CreateCommuneInput.name' of required type 'String!' was not provided."
            in err_messages
        )

    def test_gql_create_commune_invalid_field(self):
        result = self.gql.execute(
            'mutation { createCommune(details: { code: 101011, name: "FakeName" }) { name code } }'
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Unknown argument 'details' on field 'Mutation.createCommune'."
            in err_messages
        )

    def test_gql_create_commune_duplicated(self):
        result = self.gql.execute(
            'mutation { createCommune(communeDetails: { code: 13502, name: "FakeName" }) { name code } }'
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert (
            "Tried to save duplicate unique keys (E11000 Duplicate Key Error)"
            in err_messages
        )

    def test_gql_create_commune_empty_value(self):
        result = self.gql.execute(
            'mutation { createCommune(communeDetails: { code: 101011, name: "" }) { name code } }'
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert "String value is too short: ['name']" in err_messages
        assert "ValidationError" in err_messages

    def test_gql_create_commune_maintainer_not_found(self):
        result = self.gql.execute(
            """mutation {
            createCommune(communeDetails: {
                code: 10101, name: "FakeName", maintainer: "Not Exists"
                }
            ) { name code maintainer { name } userInCharge { email } }
        }"""
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'Maintainer "Not Exists" not found' in err_messages

    def test_gql_create_commune_user_not_found(self):
        result = self.gql.execute(
            """mutation {
            createCommune(communeDetails: {
                code: 10101, name: "FakeName", userInCharge: "missing@example.org"
                }
            ) { name code maintainer { name } userInCharge { email } }
        }"""
        )
        err_messages = self.assert_errors_and_get_messages(result)
        assert 'User "missing@example.org" not found' in err_messages

    def test_gql_get_junctions(self):
        result = self.gql.execute("query { junctions { jid } }")
        assert not "errors" in result
        assert len(result["data"]["junctions"]) > 0

    def test_gql_get_junctions_empty(self):
        drop_old_data()
        result = self.gql.execute("query { junctions { jid } }")
        assert not "errors" in result
        assert len(result["data"]["junctions"]) == 0

    def test_gql_get_junctions_coordinates(self):
        result = self.gql.execute(
            "query { junctions { jid metadata { location { coordinates } } } }"
        )
        assert not "errors" in result
        assert len(result["data"]["junctions"]) > 0
