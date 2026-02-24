"""数据库初始化脚本"""
from .connection import init_db


def main():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")


if __name__ == "__main__":
    main()
