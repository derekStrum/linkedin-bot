"""
Provides linkedin api-related code
"""
import random
import logging
from time import sleep
import json
import re
from math import ceil

from linkedin_api.utils.helpers import get_id_from_urn, utc_mktime, get_default_regions
from linkedin_api.client import Client

from base64 import b64encode
import secrets
from urllib.parse import urlencode


def toqs(params):
    """
    Takes a dictionary of params and returns a query string
    """

    return "&".join([f"{key}={params[key]}" for key in params.keys()])


def default_evade():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    sleep(random.randint(2, 5))  # sleep a random duration to try and evade suspention


class Linkedin(object):
    """
    Class for accessing Linkedin API.
    """

    _MAX_UPDATE_COUNT = 100  # max seems to be 100
    _MAX_SEARCH_COUNT = 49  # max seems to be 49
    _MAX_REPEATED_REQUESTS = (
        200
    )  # VERY conservative max requests count to avoid rate-limit

    def __init__(self, username, password, proxy_dict, db=None, logger=None):
        self.client = Client(proxy_dict=proxy_dict, db=db)
        self.username = username
        self.client.authenticate(username, password)
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def _fetch(self, uri, evade=default_evade, **kwargs):
        """
        GET request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL}{uri}"
        return self.client.session.get(url, **kwargs)

    def _post(self, uri, evade=default_evade, **kwargs):
        """
        POST request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL}{uri}"
        return self.client.session.post(url, **kwargs)

    def connect_with_someone(self, public_id=None, message=None):
        """
        Send a message to a given conversation. If error, return true.
        generate_tracking_id is not equal to API, gene
        """
        sleep(
            random.randint(3, 5)
        )  # sleep a random duration to try and evade suspention

        send_data = {"emberEntityName":"growth/invitation/norm-invitation","invitee":{"com.linkedin.voyager.growth.invitation.InviteeProfile":{"profileId":public_id}},"trackingId":"b5sl31fLRsSu9sj07UuEGg=="}
        if message:
            send_data['message'] = message

        payload = json.dumps(
            send_data
        )

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/growth/normInvitations",
            data=payload,
        )

        return res.status_code == 201

    def search(self, params, limit=None, results=[], blacklist=[], iteration=0):
        """
        Do a search.
        """
        count = (
            limit
            if limit and limit <= Linkedin._MAX_SEARCH_COUNT
            else Linkedin._MAX_SEARCH_COUNT
        )

        # specific hack to increase search perfomance
        if count < Linkedin._MAX_SEARCH_COUNT:
            count = Linkedin._MAX_SEARCH_COUNT

        default_params = {
            "count": str(count),
            "filters": "List()",
        }

        default_params.update(params)

        default_params.update({
            "origin": "GLOBAL_SEARCH_HEADER",
            "q": "all",
            "queryContext": "List(spellCorrectionEnabled->true,relatedSearchesEnabled->true,kcardTypes->PROFILE|COMPANY)",
            "start": iteration * count,
        })

        res = self._fetch(
            f"/search/blended?{toqs(default_params)}",
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )

        data = res.json()
        new_elements = []
        skipped_not_aviable_elements = 0
        skipped_blacklist_elements = 0

        for i in range(len(data["data"]["elements"])):
            items = data["data"]["elements"][i]["elements"]
            for item in items:
                if len(item.get('socialProofImagePile', [])) == 0:
                    skipped_not_aviable_elements += 1
                elif get_id_from_urn(item.get("targetUrn")) and get_id_from_urn(item.get("targetUrn")) in blacklist:
                    skipped_blacklist_elements += 1
                else:
                    new_elements.append(item)

            # not entirely sure what extendedElements generally refers to - keyword search gives back a single job?
            # new_elements.extend(data["data"]["elements"][i]["extendedElements"])

        self.logger.info('#{3} Skipped {0} / {1} (blacklist) elements per search iteration with {2} limit. Start {4} / Count {5} | {6}'.format(
            skipped_not_aviable_elements,
            skipped_blacklist_elements,
            limit,
            iteration,
            default_params['start'],
            default_params['count'],
            params
        ))

        results.extend(new_elements)
        # recursive base case

        total = data.get('data', {}).get('paging', {}).get('total', 0)
        if (limit is not None
                and (
                        # if our results exceed set limit
                        len(results) >= limit
                )) \
                or iteration >= Linkedin._MAX_REPEATED_REQUESTS \
                or (total and iteration >= ceil(total / count)) \
                or not total:
            return results

        self.logger.info(f"results grew to {len(results)}")
        iteration += 1
        return self.search(params, results=results, limit=limit, iteration=iteration, blacklist=blacklist)

    def search_people(
            self,
            keywords=None,
            connection_of=None,
            network_depth=None,
            current_company=None,
            past_companies=None,
            nonprofit_interests=None,
            profile_languages=None,
            regions=None,
            industries=None,
            schools=None,
            include_private_profiles=False,  # profiles without a public id, "Linkedin Member"
            max_results=49,
            black_list=[]
    ):
        """
        Do a people search.
        """

        filters = ["resultType->PEOPLE"]
        if connection_of:
            filters.append(f"connectionOf->{connection_of}")
        if network_depth:
            filters.append(f"network->{network_depth}")
        if regions:
            filters.append(f'geoRegion->{"|".join(regions)}')
        if industries:
            filters.append(f'industry->{"|".join(industries)}')
        if current_company:
            filters.append(f'currentCompany->{"|".join(current_company)}')
        if past_companies:
            filters.append(f'pastCompany->{"|".join(past_companies)}')
        if profile_languages:
            filters.append(f'profileLanguage->{"|".join(profile_languages)}')
        if nonprofit_interests:
            filters.append(f'nonprofitInterest->{"|".join(nonprofit_interests)}')
        if schools:
            filters.append(f'schools->{"|".join(schools)}')

        params = {"filters": "List({})".format(",".join(filters))}

        if keywords:
            params["keywords"] = keywords

        data = self.search(params, limit=max_results, results=[], blacklist=black_list)
        if len(data) > max_results:
            data = data[:max_results]

        out_results = []
        for item in data:
            if "publicIdentifier" not in item:
                continue
            out_results.append(
                {
                    "urn_id": get_id_from_urn(item.get("targetUrn")),
                    "distance": item.get("memberDistance", {}).get("value"),
                    "public_id": item.get("publicIdentifier"),
                    "title": item.get("title")
                }
            )

        return out_results

    def get_profile_contact_info(self, public_id=None, urn_id=None):
        """
        Return data for a single profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/identity/profiles/{public_id or urn_id}/profileContactInfo"
        )
        data = res.json()

        contact_info = {
            "email_address": data.get("emailAddress"),
            "websites": [],
            "phone_numbers": data.get("phoneNumbers", []),
        }

        websites = data.get("websites", [])
        for item in websites:
            if "com.linkedin.voyager.identity.profile.StandardWebsite" in item["type"]:
                item["label"] = item["type"][
                    "com.linkedin.voyager.identity.profile.StandardWebsite"
                ]["category"]
            elif "" in item["type"]:
                item["label"] = item["type"][
                    "com.linkedin.voyager.identity.profile.CustomWebsite"
                ]["label"]

            del item["type"]

        contact_info["websites"] = websites

        return contact_info

    def get_my_invitations(self):
        """
        """

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/relationships/invitations?folder=INBOX&start=0"
        )

        data = res.json()

        return data

    def accept_invite(self, invitation_id, invitation_shared_secret):
        """
        """

        payload = json.dumps(
            {"invitationId":invitation_id,"invitationSharedSecret":invitation_shared_secret,"isGenericInvitation":False}
        )

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/relationships/invitations/" + invitation_id + "?action=accept",
            data=payload,
        )

        return res.status_code == 200

    def accept_invites(self):
        data = self.get_my_invitations().get('elements')
        invites_accepted = 0

        if data:
            for invation in data:
                if self.accept_invite(get_id_from_urn(invation['entityUrn']), invation['sharedSecret']):
                    invites_accepted += 1
                    # Wait few time
                    random.uniform(1, 4)

        return invites_accepted

    def get_profile(self, public_id=None, urn_id=None):
        """
        Return data for a single profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        sleep(
            random.randint(2, 5)
        )  # sleep a random duration to try and evade suspention
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/identity/profiles/{public_id or urn_id}/profileView"
        )

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data["message"]))
            return {}

        # massage [profile] data
        profile = data["profile"]
        if "miniProfile" in profile:
            if "picture" in profile["miniProfile"]:
                profile["displayPictureUrl"] = profile["miniProfile"]["picture"][
                    "com.linkedin.common.VectorImage"
                ]["rootUrl"]
            profile["profile_id"] = get_id_from_urn(profile["miniProfile"]["entityUrn"])

            del profile["miniProfile"]

        del profile["defaultLocale"]
        del profile["supportedLocales"]
        del profile["versionTag"]
        del profile["showEducationOnProfileTopCard"]

        # massage [experience] data
        experience = data["positionView"]["elements"]
        for item in experience:
            if "company" in item and "miniCompany" in item["company"]:
                if "logo" in item["company"]["miniCompany"]:
                    logo = item["company"]["miniCompany"]["logo"].get(
                        "com.linkedin.common.VectorImage"
                    )
                    if logo:
                        item["companyLogoUrl"] = logo["rootUrl"]
                del item["company"]["miniCompany"]

        profile["experience"] = experience

        # massage [skills] data
        skills = [item["name"] for item in data["skillView"]["elements"]]

        profile["skills"] = skills

        # massage [education] data
        education = data["educationView"]["elements"]
        for item in education:
            if "school" in item:
                if "logo" in item["school"]:
                    item["school"]["logoUrl"] = item["school"]["logo"][
                        "com.linkedin.common.VectorImage"
                    ]["rootUrl"]
                    del item["school"]["logo"]

        profile["education"] = education

        return profile

    def get_profile_connections_raw(self, max_results=None, results=[], only_urn=False):
        sleep(
            random.randint(0, 1)
        )

        count = (
            max_results
            if max_results and max_results <= Linkedin._MAX_SEARCH_COUNT
            else Linkedin._MAX_SEARCH_COUNT
        )

        default_params = {
            "count": count,
            "start": len(results),
            "sortType": "RECENTLY_ADDED"
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/relationships/connections?" + urlencode(default_params)
        )

        data = res.json()
        total_found = data.get("paging", {}).get("count")

        # recursive base case
        if (
            len(data["elements"]) == 0
            or (max_results and len(results) >= max_results)
            or total_found is None
            or (max_results is not None and len(results) / max_results >= Linkedin._MAX_REPEATED_REQUESTS)
        ):
            if max_results and (len(results) > max_results):
                results = results[:max_results]

            return results

        if data and data.get('elements'):
            connections_list = data.get('elements')
            connections = []
            if only_urn:
                for profile in connections_list:
                    connections.append({
                        'publicIdentifier': profile.get('miniProfile', {}).get('publicIdentifier'),
                        'entityUrn': get_id_from_urn(profile['entityUrn'])
                    })
            else:
                for profile in connections_list:
                    connections.append(profile.get('miniProfile', {}))

            results = results + connections

        self.logger.info(f"results grew: {len(results)}")
        return self.get_profile_connections_raw(max_results=max_results, results=results, only_urn=only_urn)

    def get_company_updates(self, public_id=None, urn_id=None, max_results=None, results=[]):
        """"
        Return a list of company posts

        [public_id] - public identifier ie - microsoft
        [urn_id] - id provided by the related URN
        """
        sleep(
            random.randint(2, 5)
        )  # sleep a random duration to try and evade suspention

        params = {
            "companyUniversalName": {public_id or urn_id},
            "q": "companyFeedByUniversalName",
            "moduleKey": "member-share",
            "count": Linkedin._MAX_UPDATE_COUNT,
            "start": len(results),
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/feed/updates", params=params
        )

        data = res.json()

        if (
            len(data["elements"]) == 0
            or (max_results is not None and len(results) >= max_results)
            or (max_results is not None and len(results) / max_results >= Linkedin._MAX_REPEATED_REQUESTS)
        ):
            return results

        results.extend(data["elements"])
        self.logger.info(f"results grew: {len(results)}")

        return self.get_company_updates(public_id=public_id, urn_id=urn_id, results=results, max_results=max_results)

    def get_profile_updates(self, public_id=None, urn_id=None, max_results=None, results=[]):
        """"
        Return a list of profile posts

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        sleep(
            random.randint(2, 5)
        )  # sleep a random duration to try and evade suspention

        params = {
            "profileId": {public_id or urn_id},
            "q": "memberShareFeed",
            "moduleKey": "member-share",
            "count": Linkedin._MAX_UPDATE_COUNT,
            "start": len(results),
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/feed/updates", params=params
        )

        data = res.json()

        if (
            len(data["elements"]) == 0
            or (max_results is not None and len(results) >= max_results)
            or (max_results is not None and len(results) / max_results >= Linkedin._MAX_REPEATED_REQUESTS)
        ):
            return results

        results.extend(data["elements"])
        self.logger.info(f"results grew: {len(results)}")

        return self.get_profile_updates(public_id=public_id, urn_id=urn_id, results=results, max_results=max_results)

    def get_current_profile_views(self):
        """
        Get profile view statistics, including chart data.
        """
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/identity/panels"
        )

        data = res.json()

        return data['elements'][0]['value']['com.linkedin.voyager.identity.me.ProfileViewsByTimePanel']

    def get_current_entity_urn(self):
        """
        Get profile view statistics, including chart data.
        """
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/me"
        )

        data = res.json()

        return get_id_from_urn(data["miniProfile"]["entityUrn"])

    def whoami(self):
        """
        Get profile view statistics, including chart data.
        """
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/me"
        )

        data = res.json()

        return data


    def get_school(self, public_id):
        """
        Return data for a single school.

        [public_id] - public identifier i.e. uq
        """
        sleep(
            random.randint(2, 5)
        )  # sleep a random duration to try and evade suspention
        params = {
            "decoration": (
                """
                (
                autoGenerated,backgroundCoverImage,
                companyEmployeesSearchPageUrl,companyPageUrl,confirmedLocations*,coverPhoto,dataVersion,description,
                entityUrn,followingInfo,foundedOn,headquarter,jobSearchPageUrl,lcpTreatment,logo,name,type,overviewPhoto,
                paidCompany,partnerCompanyUrl,partnerLogo,partnerLogoImage,rankForTopCompanies,salesNavigatorCompanyUrl,
                school,showcase,staffCount,staffCountRange,staffingCompany,topCompaniesListName,universalName,url,
                companyIndustries*,industries,specialities,
                acquirerCompany~(entityUrn,logo,name,industries,followingInfo,url,paidCompany,universalName),
                affiliatedCompanies*~(entityUrn,logo,name,industries,followingInfo,url,paidCompany,universalName),
                groups*~(entityUrn,largeLogo,groupName,memberCount,websiteUrl,url),
                showcasePages*~(entityUrn,logo,name,industries,followingInfo,url,description,universalName)
                )
                """
            ),
            "q": "universalName",
            "universalName": public_id,
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/organization/companies", params=params
        )

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data["message"]))
            return {}

        school = data["elements"][0]

        return school

    def get_company(self, public_id):
        """
        Return data for a single company.

        [public_id] - public identifier i.e. univeristy-of-queensland
        """
        sleep(
            random.randint(2, 5)
        )  # sleep a random duration to try and evade suspention
        params = {
            "decoration": (
                """
                (
                affiliatedCompaniesWithEmployeesRollup,affiliatedCompaniesWithJobsRollup,articlePermalinkForTopCompanies,
                autoGenerated,backgroundCoverImage,companyEmployeesSearchPageUrl,
                companyPageUrl,confirmedLocations*,coverPhoto,dataVersion,description,entityUrn,followingInfo,
                foundedOn,headquarter,jobSearchPageUrl,lcpTreatment,logo,name,type,overviewPhoto,paidCompany,
                partnerCompanyUrl,partnerLogo,partnerLogoImage,permissions,rankForTopCompanies,
                salesNavigatorCompanyUrl,school,showcase,staffCount,staffCountRange,staffingCompany,
                topCompaniesListName,universalName,url,companyIndustries*,industries,specialities,
                acquirerCompany~(entityUrn,logo,name,industries,followingInfo,url,paidCompany,universalName),
                affiliatedCompanies*~(entityUrn,logo,name,industries,followingInfo,url,paidCompany,universalName),
                groups*~(entityUrn,largeLogo,groupName,memberCount,websiteUrl,url),
                showcasePages*~(entityUrn,logo,name,industries,followingInfo,url,description,universalName)
                )
                """
            ),
            "q": "universalName",
            "universalName": public_id,
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/organization/companies", params=params
        )

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data["message"]))
            return {}

        company = data["elements"][0]

        return company

    def get_conversation_details(self, profile_urn_id):
        """
        Return the conversation (or "message thread") details for a given [public_profile_id]
        """
        # passing `params` doesn't work properly, think it's to do with List().
        # Might be a bug in `requests`?
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/messaging/conversations?\
            keyVersion=LEGACY_INBOX&q=participants&recipients=List({profile_urn_id})"
        )

        data = res.json()

        if data and data.get('elements'):
            item = data["elements"][0]
            item["id"] = get_id_from_urn(item["entityUrn"])
        else:
            item = None

        return item

    def get_conversations(self):
        """
        Return list of conversations the user is in.
        """
        params = {"keyVersion": "LEGACY_INBOX"}

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/messaging/conversations", params=params
        )

        return res.json()

    def get_conversation(self, conversation_urn_id):
        """
        Return the full conversation at a given [conversation_urn_id]
        """
        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/messaging/conversations/{conversation_urn_id}/events"
        )

        return res.json()

    def send_message(self, conversation_urn_id, message_body):
        """
        Send a message to a given conversation. If error, return true.
        """
        params = {"action": "create"}

        payload = json.dumps(
            {
                "eventCreate": {
                    "value": {
                        "com.linkedin.voyager.messaging.create.MessageCreate": {
                            "body": message_body,
                            "attachments": [],
                            "attributedBody": {"text": message_body, "attributes": []},
                            "mediaAttachments": [],
                        }
                    }
                }
            }
        )

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/messaging/conversations/{conversation_urn_id}/events",
            params=params,
            data=payload,
        )

        return res.status_code == 201

    def comment_on_post(self, format, post_id, message):
        """
        Send a message to a given post
        """

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/me"
        )

        data = res.json()

        payload = json.dumps(
            {
                "comment":{
                    "values": [
                        {
                            "value": message
                        }
                    ]
                },
                "commenter":{
                    "com.linkedin.voyager.feed.MemberActor":{
                        "actorType":"member",
                        "profileRoute":"profile.view",
                        "emberEntityName":"feed/member-actor",
                        "miniProfile": data['miniProfile']
                    }
                },
                "commentSocialDetail":{
                    "threadId":"{0}:{1}".format(format, post_id)
                },
                "createdTime":int(utc_mktime()),
                "threadId":"{0}:{1}".format(format, post_id),
                "urn":"urn:li:comment:{0}:{1}".format(format, post_id),
                "index":0
            }
        )

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/feed/comments",
            data=payload,
        )

        try:
            restli_id = res.headers.get('x-restli-id', '')
            restli_id = re.search('(\d+\,\d+)', restli_id)
            restli_id = restli_id.group(1)
        except Exception:
            restli_id = None
            pass

        return res.status_code == 201, restli_id

    def delete_comment(self, ugs_post):
        """
        Delete comment
        """

        res = self.client.session.delete(
            f"{self.client.API_BASE_URL}/feed/comments/urn:li:comment:(activity:{ugs_post})",
        )

        return res.status_code == 200

    def create_conversation(self, conversation_urn_id, message_body):
        """
        Send a message to a given conversation. If error, return true.
        """

        payload = json.dumps(
            {
                "keyVersion": "LEGACY_INBOX",
                "conversationCreate": {
                    "eventCreate": {
                        # "originToken": "3c809d5d-c58a-49b8-801d-9d42607db1c5", TODO: UNKNOWN FILED, just skipped
                        "value": {
                            "com.linkedin.voyager.messaging.create.MessageCreate": {
                                "body": message_body,
                                "attachments": [],
                                "attributedBody": {
                                    "attributes": [],
                                    "text": message_body
                                }
                            }
                        }
                    },
                    "recipients": [
                        conversation_urn_id
                    ],
                    "subtype": "MEMBER_TO_MEMBER"
                }
            }
        )

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/messaging/conversations?action=create",
            data=payload,
        )

        return res.status_code == 201

    def mark_conversation_as_seen(self, conversation_urn_id):
        """
        Send seen to a given conversation. If error, return True.
        """
        payload = json.dumps({
            "patch": {
                "$set": {
                    "read": True
                }
            }
        })

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/messaging/conversations/{conversation_urn_id}",
            data=payload
        )

        return res.status_code != 200

    def generate_tracking_id(self, length=16):
        return b64encode(secrets.token_bytes(length)).decode()

    def get_regions(self):
        """
        """
        input_regions = get_default_regions()
        output_regions = {}
        for region in input_regions:
            res = self.client.session.get(
                f"{self.client.API_BASE_URL}/typeahead/hits?q=federated&query={region}&shouldUseSchoolParams=false&types=List(REGION)"
            )

            data = res.json()
            elements = data.get('elements', [])
            for element in elements:
                country_id = element.get('hitInfo', {}).get('com.linkedin.voyager.typeahead.TypeaheadRegion', {}).get('id')
                if country_id:
                    output_regions.setdefault(region, {}).setdefault('data', []).append(country_id)
                    self.logger.info(output_regions)

        # Normalize
        for key, value in output_regions.items():
            value['merged'] = '|'.join(value['data'])

        return output_regions
