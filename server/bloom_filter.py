class BloomFilter:
    def __init__(self, size: int, hash_functions: list):
        """
        Инициализация фильтра Блума.
        
        :param size: Размер битового массива (количество бит)
        :param hash_functions: Список хеш-функций. Каждая функция должна принимать ключ и возвращать целое число.
        """
        self.size = size
        self.hash_functions = hash_functions
        # Создаем битовый массив с использованием bytearray
        self.bit_array = bytearray((size + 7) // 8)  # Выделяем достаточно байт

    def _set_bit(self, position: int):
        """Устанавливает бит в позиции position в 1."""
        byte_index = position // 8
        bit_offset = position % 8
        self.bit_array[byte_index] |= (1 << bit_offset)

    def _get_bit(self, position: int) -> bool:
        """Проверяет, установлен ли бит в позиции position."""
        byte_index = position // 8
        bit_offset = position % 8
        return (self.bit_array[byte_index] & (1 << bit_offset)) != 0

    def insert(self, key):
        """Добавляет ключ в фильтр."""
        for hash_func in self.hash_functions:
            # Применяем хеш-функцию и берем модуль от размера
            position = hash_func(key) % self.size
            self._set_bit(position)

    def search(self, key) -> bool:
        """Проверяет наличие ключа в фильтре (может возвращать ложноположительные срабатывания)."""
        for hash_func in self.hash_functions:
            position = hash_func(key) % self.size
            if not self._get_bit(position):
                return False
        return True
