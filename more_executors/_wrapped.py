from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from more_executors._wrap import CanCustomizeBind


class CustomizableThreadPoolExecutor(CanCustomizeBind, ThreadPoolExecutor):
    pass


class CustomizableProcessPoolExecutor(CanCustomizeBind, ProcessPoolExecutor):
    pass
