from dataclasses import dataclass

@dataclass(frozen=True)
class UserAttributes:
    username: str
    user_displayname: str
    email: str = ""
    department: str = ""
    title: str = ""
    phone: str = ""
    company: str = ""
    manager: str = ""
    distinguished_name: str = ""
    object_guid: str = ""

    @classmethod
    def from_aduser(cls, ad_user):
        def get_attribute(attr):
            val = ad_user.get_attribute(attr)
            return val[0] if isinstance(val, list) and val else ""
        return cls(
            username=get_attribute('sAMAccountName').lower(),
            user_displayname=get_attribute('displayName'),
            email=get_attribute('mail'),
            department=get_attribute('department'),
            title=get_attribute('title'),
            phone=get_attribute('telephoneNumber'),
            company=get_attribute('company'),
            manager=get_attribute('manager'),
            distinguished_name=get_attribute('distinguishedName'),
            object_guid=get_attribute('objectGUID')
        )