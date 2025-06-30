from rich import print

from config.settings import settings
from utils.logging import logger
from utils.exceptions import OllamaConnectionError

def main():
    print(settings)

    return 0


if __name__ == "__main__":
    main()
