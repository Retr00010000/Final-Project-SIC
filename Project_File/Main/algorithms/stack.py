class StackOverflowError(Exception):
  pass
class StackUnderflowError(Exception):
  pass

class Stack:
  def __init__(self,capacity:int=5):
    self._capacity = capacity
    self._items = []

  def is_empty(self):
    return len(self._items) == 0

  def is_full(self):
    return len(self._items) >= self._capacity

  def size(self):
    return len(self._items)

  def get_all(self):
    return list(self._items)

  def push(self, item):
    if self.is_full():
      raise StackOverflowError("Lane is full , You can't add new car ...")
    self._items.append(item)

  def pop(self):
    if self.is_empty():
      raise StackUnderflowError("Lane is empty , You can't remove ...")
    return self._items.pop()

  def peek(self):
    if self.is_empty():
      return None
    return self._items[-1]
  
  def retrieve_car(self, target_plate):
      if self.is_empty():
        return False, ["Lane is empty!"]

      temp_stack = Stack(capacity=self._capacity)
      steps = []
      found = False

      while not self.is_empty():
        current_car = self.pop()
        if current_car == target_plate:
          found = True
          steps.append(f"Found target car: {target_plate} (Retrieved)")
          break
        else:
          temp_stack.push(current_car)
          steps.append(f"Temporarily moved {current_car} out of the way")

      while not temp_stack.is_empty():
        car_to_restore = temp_stack.pop()
        self.push(car_to_restore)
        steps.append(f"Restored {car_to_restore} back to the lane")
      if not found:
        steps.append(f"Car {target_plate} was not found in the lane.")
      return found,steps
  






  