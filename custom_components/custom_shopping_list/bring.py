#!/usr/bin/env python
# coding: utf8
from __future__ import annotations

from json import JSONDecodeError
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union

from aiohttp import ClientResponse, ClientSession, InvalidURL

JSON = Union[Dict[str, Any], List[Dict[str, Any]]]

"""
This inofficial API is based on the reverse engineering by helvete003
https://github.com/helvete003/bring-api
Thanks for his work!

For information about Bring! please see getbring.com

Everybody feel free to use it, but without any liability or warranty.

Bring! as a Service and Brand is property of Bring! Labs AG
This API was just build because the app is really great and
its users want to include it in any part of their life.
It can be unavailable when ever Bring! Labs decides to publish an official API,
or want's this API to be disabled.

Until then: Thanks to Bring! Labs for their great service!

Made with ❤ and no ☕ in Germany
"""


class AuthentificationFailed(Exception):
    pass


class BringApi:
    def __init__(
        self, username: str, password: str, session: ClientSession = None,
    ) -> None:
        self.username = username
        self.password = password
        self._bringRestURL = "https://api.getbring.com/rest/"
        self._translations = None
        self.bringUUID = ""
        self.bringListUUID = ""
        self.headers = {}
        self.addheaders = {}
        self.session = session if session else ClientSession()
        self.logged = False

    async def __aenter__(self) -> BringApi:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.close()

    @staticmethod
    async def check_response(response: ClientResponse) -> None:
        """ Check the response returned by the TaHoma API"""
        if response.status in [200, 204]:
            return
        try:
            result = await response.json(content_type=None)
        except JSONDecodeError:
            result = await response.text()
        if result.get("errorCode"):
            message = result.get("error")

        raise Exception(message if message else result)

    async def __get(
        self,
        endpoint: str,
        headers: Optional[JSON] = None,
        payload: Optional[JSON] = None,
        data: Optional[JSON] = None,
        params: Optional[JSON] = None,
    ) -> Any:
        """ Make a GET request to the TaHoma API """
        async with self.session.get(
            f"{self._bringRestURL}{endpoint}", headers=headers, data=data, json=payload, params=params,
        ) as response:
            await self.check_response(response)
            return await response.json()

    async def __put(
        self,
        endpoint: str,
        headers: Optional[JSON] = None,
        payload: Optional[JSON] = None,
        data: Optional[JSON] = None,
        params: Optional[JSON] = None,
    ) -> None:
        """ Make a PUT request to the TaHoma API """
        async with self.session.put(
            f"{self._bringRestURL}{endpoint}", headers=headers, data=data, json=payload, params=params,
        ) as response:
            await self.check_response(response)

    async def login(self) -> None:
        try:
            params = {"email": self.username, "password": self.password}
            login = await self.__get("bringlists", params=params)
            self.bringUUID = login["uuid"]
            self.bringListUUID = login["bringListUUID"]
            self.headers = {
                "X-BRING-API-KEY": "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp",
                "X-BRING-CLIENT": "android",
                "X-BRING-USER-UUID": self.bringUUID,
                "X-BRING-VERSION": "303070050",
                "X-BRING-COUNTRY": "de",
            }
            self.addheaders = {
                "X-BRING-API-KEY": "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp",
                "X-BRING-CLIENT": "android",
                "X-BRING-USER-UUID": self.bringUUID,
                "X-BRING-VERSION": "303070050",
                "X-BRING-COUNTRY": "de",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            self.logged = True
        except (InvalidURL, ValueError):
            raise AuthentificationFailed("email password combination not existing")

    async def close(self) -> None:
        """Close the session."""
        await self.session.close()

    # return list of items from current list as well as recent items - translated if requested
    async def get_items(self, locale=None) -> dict:
        if not self.logged:
            await self.login()

        items = await self.__get(
            f"bringlists/{self.bringListUUID}", headers=self.headers
        )

        if locale:
            transl = self.load_translations(locale)
            for item in items["purchase"]:
                item["name"] = transl.get(item["name"]) or item["name"]
            for item in items["recently"]:
                item["name"] = transl.get(item["name"]) or item["name"]
        return items

    # return the details: Name, Image, UUID
    async def get_items_detail(self) -> dict:
        items = await self.__get(
            f"bringlists/{self.bringListUUID}/details", headers=self.headers,
        )
        return items

    # add a new item to the current list with a given specification = additional description
    async def purchase_item(self, item, specification: str = None):
        params = {"purchase": item}
        if specification:
            params["specification"] = specification
        await self.__put(
            f"bringlists/{self.bringListUUID}", params=params, headers=self.addheaders,
        )

    # add/move something to the recent items
    async def recent_item(self, item):
        params = {"recently": item}
        await self.__put(
            f"bringlists/{self.bringListUUID}", params=params, headers=self.addheaders,
        )

    # remove an item completely (from recent and purchase)
    async def remove_item(self, item):
        params = {"remove": item}
        await self.__put(
            f"bringlists/{self.bringListUUID}", params=params, headers=self.addheaders,
        )

    # search for an item in the list
    # NOT WORKING!
    async def search_item(self, search):
        params = {"listUuid": self.bringListUUID, "itemId": search}
        return await self.__get("bringlistitemdetails/", params=params, headers=self.headers,)

    # // Hidden Icons? Don't know what this is used for
    async def load_products(self):
        return await self.__get(("bringproducts", headers=self.headers)

    # // Found Icons? Don't know what this is used for
    async def load_features(self):
        return await self.__get(
            f"bringusers/{self.bringUUID}/features", headers=self.headers,
        )

    # load all list infos
    async def load_lists(self):
        return await self.__get(f"bringusers/{self.bringUUID}/lists", headers=self.headers,)

    # get list of all users in list ID
    async def get_users_from_list(self, listUUID):
        return await self.__get(f"bringlists/{listUUID}/users", headers=self.headers)

    # get settings from user
    async def get_user_settings(self):
        return await self.__get(f"bringusersettings/{self.bringUUID}", headers=self.headers,)

    # Load translation file e. g. via 'de-DE'
    async def load_translations(self, locale):
        if not self._translations:
            self._translations = await self.__get(
                f"https://web.getbring.com/locale/articles.{locale}.json"
            )
        return self._translations

    async def translate_to_ch(self, item: str, locale) -> str:
        for val, key in self.load_translations(locale).items():
            if key == item:
                return val
        return item

    # Load localized catalag of items
    async def load_catalog(self, locale):
        return self.__get(f"https://web.getbring.com/locale/catalog.{locale}.json")
