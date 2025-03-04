from sqlalchemy.sql.functions import current_date


def date_age(birth_date):
    age = current_date - birth_date
    return age