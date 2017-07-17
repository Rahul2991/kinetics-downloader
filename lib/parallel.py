from multiprocessing import Process, Queue

import lib.downloader as downloader

class Pool:
  """
  A pool of video downloaders.
  """

  def __init__(self, classes, videos_dict, directory, num_workers, failed_save_file, compress):
    """
    :param classes:               List of classes to download.
    :param videos_dict:           Dictionary of all videos.
    :param directory:             Where to download to videos.
    :param num_workers:           How many videos to download in parallel.
    :param failed_save_file:      Where to save the failed videos ids.
    :param compress:              Whether to compress the videos using gzip.
    """
    self.classes = classes
    self.videos_dict = videos_dict
    self.directory = directory
    self.num_workers = num_workers
    self.failed_save_file = failed_save_file
    self.compress = compress

    self.videos_queue = Queue(100)
    self.failed_queue = Queue(100)

    self.workers = []
    self.failed_save_worker = None

  def feed_videos(self):
    """
    Feed video ids into the download queue.
    :return:    None.
    """
    for class_name in self.classes:
      downloader.download_class_parallel(class_name, self.videos_dict, self.directory, self.videos_queue)

  def start_workers(self):
    """
    Start all workers.
    :return:    None.
    """
    # start failed videos saver
    if self.failed_save_file is not None:
      self.failed_save_worker = Process(target=write_failed_worker, args=(self.failed_queue, self.failed_save_file))
      self.failed_save_worker.start()

    # start download workers
    for _ in range(self.num_workers):
      worker = Process(target=video_worker, args=(self.videos_queue, self.failed_queue, self.compress))
      worker.start()
      self.workers.append(worker)

  def stop_workers(self):
    """
    Stop all workers.
    :return:    None.
    """
    # send end signal to all download workers
    for _ in range(len(self.workers)):
      self.videos_queue.put(None)

    # wait for the processes to finish
    for worker in self.workers:
      worker.join()

    # end failed videos saver
    if self.failed_save_worker is not None:
      self.failed_queue.put(None)
      self.failed_save_worker.join()

def video_worker(videos_queue, failed_queue, compress):
  """
  Downloads videos pass in the videos queue.
  :param videos_queue:      Queue for metadata of videos to be download.
  :param failed_queue:      Queue of failed video ids.
  :param compress:          Whether to compress the videos using gzip.
  :return:                  None.
  """

  while True:
    request = videos_queue.get()

    if request is None:
      break

    video_id, directory, start, end = request

    if not downloader.process_video(video_id, directory, start, end, compress=compress):
      failed_queue.put(video_id)

def write_failed_worker(failed_queue, failed_save_file):
  """
  Write failed video ids into a file.
  :param failed_queue:        Queue of failed video ids.
  :param failed_save_file:    Where to save the videos.
  :return:                    None.
  """

  file = open(failed_save_file, "a")

  while True:
    video_id = failed_queue.get()

    if video_id is None:
      break

    file.write("{}\n".format(video_id))

  file.close()