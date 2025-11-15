from typing import Self

from expanse.support.exceptions.frame import Frame


class FrameCollection(list[Frame]):
    def __init__(self, frames: list[Frame] | None = None, count: int = 0) -> None:
        if frames is None:
            frames = []

        super().__init__(frames)

        self._count: int = count

    @property
    def repetitions(self) -> int:
        return self._count - 1

    def is_repeated(self) -> bool:
        return self._count > 1

    def increment_count(self, increment: int = 1) -> Self:
        self._count += increment

        return self

    def compact(self) -> list[Self]:
        """
        Compacts the frames to deduplicate recursive calls.
        """
        collections: list[Self] = []
        current_collection = self.__class__()

        i = 0
        while i < len(self):
            frame = self[i]
            if frame in self[i + 1 :]:
                duplicate_indices = []
                for sub_index, sub_frame in enumerate(self[i + 1 :]):
                    if frame == sub_frame:
                        duplicate_indices.append(sub_index + i + 1)

                found_duplicate = False
                for duplicate_index in duplicate_indices:
                    collection = self.__class__(self[i:duplicate_index])
                    if collection == current_collection:
                        current_collection.increment_count()
                        i = duplicate_index
                        found_duplicate = True
                        break

                if found_duplicate:
                    continue

                collections.append(current_collection)
                current_collection = self.__class__(self[i : duplicate_indices[0]])

                i = duplicate_indices[0]

                continue

            if current_collection.is_repeated():
                collections.append(current_collection)
                current_collection = self.__class__()

            current_collection.append(frame)
            i += 1

        collections.append(current_collection)

        return collections
