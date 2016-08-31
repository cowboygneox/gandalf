class User:
    def __init__(self, user_id, username, hashed_password):
        self.user_id = user_id
        self.username = username
        self.hashed_password = hashed_password


class DBAdapter:
    def get_user(self, username) -> User:
        return False

    def create_user(self, user_id, username, password):
        pass

    def update_user_password(self, user_id, password):
        pass