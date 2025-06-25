from os import getenv


def get_db_url() -> str:
    # Проверяем, есть ли готовый DB_URL (для Supabase)
    db_url = getenv("DB_URL")
    if db_url:
        return db_url
    
    # Если нет готового URL, собираем из компонентов
    db_driver = getenv("DB_DRIVER", "postgresql+psycopg")
    db_user = getenv("DB_USER")
    db_pass = getenv("DB_PASS", getenv("DB_PASSWORD"))  # Поддерживаем оба варианта
    db_host = getenv("DB_HOST")
    db_port = getenv("DB_PORT")
    db_database = getenv("DB_DATABASE", getenv("DB_NAME"))  # Поддерживаем оба варианта
    db_scheme = getenv("DB_SCHEME", "public")  # Дефолтная схема

    
    # Формируем URL с параметрами схемы
    base_url = "{}://{}{}@{}:{}/{}".format(
        db_driver,
        db_user,
        f":{db_pass}" if db_pass else "",
        db_host,
        db_port,
        db_database,
    )
    
    # Добавляем схему и SSL параметры для Supabase
    ssl_params = "sslmode=require&sslcert=&sslkey=&sslrootcert="
    return f"{base_url}?options=-csearch_path%3D{db_scheme}&{ssl_params}"
