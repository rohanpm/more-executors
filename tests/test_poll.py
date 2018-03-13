from concurrent.futures import ThreadPoolExecutor
from pytest import fixture
from hamcrest import assert_that, equal_to, calling, raises, has_length
from functools import partial
from six.moves.queue import Queue
from threading import Event

from more_executors.poll import PollExecutor

from .util import assert_soon


@fixture
def executor():
    return ThreadPoolExecutor()


def poll_tasks(tasks, poll_descriptors):
    for descriptor in poll_descriptors:
        task_id = descriptor.result
        status = tasks.get(task_id)
        if status == 'done':
            descriptor.yield_result('done')
        elif status == 'error':
            descriptor.yield_exception(RuntimeError('task failed: %s' % task_id))


def test_basic_poll(executor):
    task_id_queue = Queue()
    tasks = {}
    poll_fn = partial(poll_tasks, tasks)
    poll_executor = PollExecutor(executor, poll_fn, 0.01)

    def make_task(x):
        return '%s-%s' % (x, task_id_queue.get(True))

    inputs = ['a', 'b', 'c']
    futures = [poll_executor.submit(make_task, x) for x in inputs]

    # The futures should not currently be able to progress.
    assert_that(not any([f.done() for f in futures]))

    # Allow tasks to be created.
    task_id_queue.put('x')
    task_id_queue.put('y')
    task_id_queue.put('z')

    # Insert some task statuses for the poll function to detect.
    # Note that we can't guess which thread got which queue item,
    # so let's just spam with every combination
    tasks['a-x'] = 'done'
    tasks['a-y'] = 'done'
    tasks['a-z'] = 'done'
    tasks['b-x'] = 'error'
    tasks['b-y'] = 'error'
    tasks['b-z'] = 'error'
    # Leave c with no result

    # Future a should become resolved
    assert_that(futures[0].result(10), equal_to('done'))

    # Future b should raise an exception
    assert_that(calling(futures[1].result).with_args(10), raises(RuntimeError, 'task failed'))

    # Future c should still be waiting
    assert_that(not futures[2].done())


def test_cancel_during_poll(executor):
    task_ran = Event()
    poll_ran = Event()
    last_descriptors = []

    def poll_fn(descriptors):
        while last_descriptors:
            last_descriptors.pop()
        last_descriptors.extend(descriptors)
        poll_ran.set()

    def fn():
        task_ran.set()
        return 123

    poll_executor = PollExecutor(executor, poll_fn, 0.01)
    future = poll_executor.submit(fn)

    # It shouldn't finish yet.
    assert_that(not future.done())

    # Wait until the delegate has definitely started executing.
    task_ran.wait(10)

    # To determine once the submitted function has completed, we can
    # wait until 'running' is no longer true.
    assert_soon(lambda: assert_that(not future.running()))

    # Wait until next poll
    poll_ran.clear()
    poll_ran.wait(10.0)

    # Poll function should have been passed the result of fn
    assert_that(last_descriptors[0].result, equal_to(123))

    # It should be possible to cancel the future
    assert_that(future.cancel())

    # Wait until next poll
    poll_ran.clear()
    poll_ran.wait(10.0)

    # The cancelled future should have been removed from the
    # descriptors passed to the poll function
    assert_that(last_descriptors, equal_to([]))

    # It should be harmless to request cancel again
    assert_that(future.cancel())


def test_cancel_during_poll_fn(executor):
    queue = Queue()
    poll_ran = Event()
    last_descriptors = []

    def poll_fn(descriptors):
        while last_descriptors:
            last_descriptors.pop()
        last_descriptors.extend(descriptors)
        poll_ran.set()

        should_process = queue.get(True)
        if should_process:
            for descriptor in descriptors:
                if descriptor.result == 'pass':
                    descriptor.yield_result('pass')
                else:
                    descriptor.yield_exception(RuntimeError('fail'))

    poll_executor = PollExecutor(executor, poll_fn, 0.01)
    futures = [poll_executor.submit(lambda x: x, x) for x in ('pass', 'fail')]

    # Wait until both futures move to polling mode.
    def wait_two_futures():
        poll_ran.clear()
        queue.put(False)
        poll_ran.wait()
        assert_that(last_descriptors, has_length(2))

    assert_soon(wait_two_futures)

    # OK, now wait until the poll function is in the middle of executing
    poll_ran.clear()
    queue.put(False)
    poll_ran.wait()

    # Cancel the futures while poll function is in progress
    assert_that(futures[0].cancel())
    assert_that(futures[1].cancel())

    # Now let the poll function proceed, and attempt to update the futures
    poll_ran.clear()
    queue.put(True)
    poll_ran.wait()

    # The futures should remain cancelled
    assert_that(futures[0].cancelled())
    assert_that(futures[1].cancelled())

    # And they should not be passed to the poll function any more
    assert_that(last_descriptors, equal_to([]))


def test_poll_fail(executor):
    task_id_queue = Queue()
    tasks = {}
    poll_should_fail = [False]
    poll_ran = Event()

    last_descriptors = []

    def poll_fn(descriptors):
        while last_descriptors:
            last_descriptors.pop()
        last_descriptors.extend(descriptors)
        poll_ran.set()
        if poll_should_fail[0]:
            raise RuntimeError("simulated poll error")
        return poll_tasks(tasks, descriptors)

    poll_executor = PollExecutor(executor, poll_fn, 0.01)

    def make_task(x):
        return '%s-%s' % (x, task_id_queue.get(True))

    inputs = ['a', 'b', 'c']
    futures = [poll_executor.submit(make_task, x) for x in inputs]

    # The futures should not currently be able to progress.
    assert_that(not any([f.done() for f in futures]))

    # Allow tasks to be created.
    task_id_queue.put('x')
    task_id_queue.put('y')
    task_id_queue.put('z')

    # Let one of the tasks complete
    tasks['a-x'] = 'done'
    tasks['a-y'] = 'done'
    tasks['a-z'] = 'done'

    # Future a should become resolved
    assert_that(futures[0].result(10), equal_to('done'))

    # Now set up the poll function to fail
    poll_should_fail[0] = True

    # That should make both remaining futures fail
    assert_that(
        calling(futures[1].result).with_args(10),
        raises(RuntimeError, 'simulated poll error'))

    assert_that(
        calling(futures[2].result).with_args(10),
        raises(RuntimeError, 'simulated poll error'))

    # Wait for the next poll
    poll_ran.clear()
    poll_ran.wait(10)

    # The failed futures should no longer be passed into the poll function
    assert_that(last_descriptors, equal_to([]))
