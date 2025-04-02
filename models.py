class User:
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash

class PromotionalPost:
    def __init__(self, id, title, content, image_url=None, external_link=None, created_at=None):
        self.id = id
        self.title = title
        self.content = content
        self.image_url = image_url
        self.external_link = external_link
        self.created_at = created_at

class WelcomeConfig:
    def __init__(self, message, enabled=True):
        self.message = message
        self.enabled = enabled

class BotConfig:
    def __init__(self, token, group_id, active=False, interval=10):
        self.token = token
        self.group_id = group_id
        self.active = active
        self.interval = interval

class Stats:
    def __init__(self, welcome_messages_sent=0, promo_messages_sent=0, last_restarted=None):
        self.welcome_messages_sent = welcome_messages_sent
        self.promo_messages_sent = promo_messages_sent
        self.last_restarted = last_restarted
