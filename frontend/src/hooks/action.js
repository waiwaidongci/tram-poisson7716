export function handler(control, feedback, task) {
  return async event => {
    event.preventDefault();
    if (control.disabled) return;
    control.disabled = true;
    feedback.textContent = '';
    try { await task(event); }
    catch (error) { feedback.textContent = error.message || '操作失败，请重试'; }
    finally { control.disabled = false; }
  };
}

export async function poll(task, isDone, active) {
  for (let count = 0; count < 45 && active(); count += 1) {
    const item = await task();
    if (isDone(item)) return item;
    await new Promise(resolve => setTimeout(resolve, 650));
  }
  return null;
}
