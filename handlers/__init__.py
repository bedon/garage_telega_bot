import pkgutil
import importlib
import inspect

# Список всех обработчиков
handlers = []

# Автоматически ищем все модули в пакете handlers
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name == "message_handler":
        continue  # Пропускаем message_handler.py, он не обработчик сообщений

    module = importlib.import_module(f"{__name__}.{module_name}")

    # Перебираем все классы в модуле
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Проверяем, что класс определён в нашем модуле, а не импортирован
        if obj.__module__ == module.__name__:
            # Проверяем наличие методов can_handle и handle
            if hasattr(obj, "can_handle") and hasattr(obj, "handle"):
                handlers.append(obj)
