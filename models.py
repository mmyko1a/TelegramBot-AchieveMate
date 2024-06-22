from peewee import SqliteDatabase, Model, CharField, DateField, ForeignKeyField, BooleanField, IntegerField

db = SqliteDatabase('bot.sqlite3')

class User(Model):
    chat_id = CharField()

    class Meta:
        database = db

class Goal(Model):
    task = CharField()
    is_done = BooleanField()
    date = DateField()
    user = ForeignKeyField(User)
    user_goal_number = IntegerField()

    class Meta:
        database = db

if __name__ == '__main__':
    db.create_tables([User, Goal])
