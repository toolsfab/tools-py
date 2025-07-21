from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, Any, Tuple, List
import traceback


def run_in_parallel(
    tasks: Iterable[Callable],
    max_workers: int = None,
) -> Tuple[List[Any], List[str]]:
    """
    Execute tasks in parallel using ThreadPoolExecutor.
    
    Args:
        tasks: Iterable of callables to execute
        max_workers: Maximum number of worker threads

    Returns:
        a Tuple containing:
            list: of results returned by tasks
            list: of exceptions occurred during tasks execution

    Example:
        from functools import partial
        def task(x):
            return x * x
        
        results = run_in_parallel([partial(task, 1), partial(task, 2)])
        # Returns ([1, 4], [])
    """
    
    results = []
    exceptions = []
    
    with ThreadPoolExecutor(max_workers) as executor:
        futures = [executor.submit(task) for task in tasks]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                exceptions.append(traceback.format_exc())

    return results, exceptions