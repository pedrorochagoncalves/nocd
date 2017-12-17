import requests

class Gistapi(object):

    def __init__(self, gist_url):
        self.gist_url = gist_url

    def get_dashboards(self, profile):
        if not profile:
            raise TypeError

        return requests.get(self.gist_url).json()[profile]