import random
from datetime import date, timedelta

from lingua_franca.format import nice_date
from lingua_franca.parse import extract_number
from ovos_workshop.decorators import intent_handler
from ovos_workshop.decorators import resting_screen_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills import OVOSSkill
from requests_cache import CachedSession


class XKCDSkill(OVOSSkill):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.settings.get("idle_random"):
            self.settings["idle_random"] = True
        self.session = CachedSession(backend='memory',
                                     expire_after=timedelta(hours=6))
        self.current_comic = 0

    def initialize(self):
        self.add_event('skill-xkcd.jarbasskills.home', self.handle_homescreen)
        self.gui.register_handler('skill-xkcd.jarbasskills.next',
                                  self.handle_next_comic)
        self.gui.register_handler('skill-xkcd.jarbasskills.prev',
                                  self.handle_prev_comic)

    # xkcd api
    def get_comic(self, number):
        return self.session.get("http://xkcd.com/" + str(number) +
                                "/info.0.json").json()

    def total_comics(self):
        return self.get_latest()["num"]

    def get_latest(self):
        return self.session.get("http://xkcd.com/info.0.json").json()

    # homescreen
    def handle_homescreen(self, message):
        self.current_comic = self.total_comics()
        self.display_comic()

    # idle screen
    @resting_screen_handler("xkcd")
    def idle(self):
        if not self.settings.get("idle_random"):
            self.update_latest()
            self.gui.show_image(self.settings["imgLink"],
                                fill='PreserveAspectFit')
            number = self.total_comics()
        else:
            number = random.randint(1, self.total_comics())
            data = self.get_comic(number)
            url = data["img"]
            title = data["safe_title"]
            self.gui.show_image(url, title=title, fill='PreserveAspectFit')
        self.set_context("XKCD", number)

    def update_latest(self):
        try:
            self.settings["raw_data"] = self.get_latest()
            comic_date = date(day=int(self.settings["raw_data"]["day"]),
                              month=int(self.settings["raw_data"]["month"]),
                              year=int(self.settings["raw_data"]["year"]))
            self.settings["imgLink"] = self.settings["raw_data"]["img"]
            self.settings["title"] = self.settings["raw_data"]["safe_title"]
            self.settings["caption"] = self.settings["raw_data"]["alt"]
            self.settings["date"] = str(comic_date)
            self.settings["spoken_date"] = nice_date(comic_date,
                                                     lang=self.lang)

        except Exception as e:
            self.log.exception(e)
        self.current_comic = self.total_comics()
        self.gui['imgLink'] = self.settings['imgLink']
        self.gui['title'] = self.settings['title']
        self.gui['date'] = self.settings['date']
        self.gui['spoken_date'] = self.settings['spoken_date']
        self.gui['caption'] = self.settings['caption']

    # intents
    @intent_handler("total_comics.intent")
    def handle_total_xkcd_intent(self, message):
        self.speak_dialog("xkcd_total_comics", {"number": self.total_comics()})
        self.gui.show_text(str(self.total_comics()) + " comics")

    @intent_handler("xkcd_website.intent")
    def handle_website_xkcd_intent(self, message):
        self.gui.show_url("https://xkcd.com/", override_idle=True)

    @intent_handler("latest_xkcd.intent")
    def handle_xkcd_intent(self, message):
        self.display_comic(self.total_comics())

    @intent_handler("xkcd_comic.intent")
    def handle_xkcd_comic_intent(self, message):
        number = extract_number(message.data["utterance"],
                                lang=self.lang,
                                ordinals=True)
        total = self.total_comics()
        if number > total:
            self.speak_dialog("num_error", {"total": total})
            self.gui.show_text(str(total) + " comics")
            return
        self.current_comic = number
        self.display_comic(number)

    @intent_handler("random_xkcd_comic.intent")
    def handle_xkcd_random_intent(self, message):
        number = random.randint(1, self.total_comics())
        self.display_comic(number)

    @intent_handler(
        IntentBuilder("PrevXKCDIntent").require("previous").optionally(
            "picture").require("XKCD"))
    def handle_prev_comic(self, message=None):
        number = self.current_comic - 1
        if number < 1:
            number = 1
        self.display_comic(number)

    @intent_handler(
        IntentBuilder("NextXKCDIntent").require("next").optionally(
            "picture").require("XKCD"))
    def handle_next_comic(self, message=None):
        number = self.current_comic + 1
        if number > self.total_comics():
            number = self.total_comics()
        self.display_comic(number)

    def display_comic(self, number=None, speak=True):
        self.gui.clear()
        number = number or self.current_comic
        self.current_comic = number
        data = self.get_comic(number)
        self.gui['imgLink'] = data["img"]
        self.gui['title'] = data["safe_title"]
        self.gui['caption'] = data["alt"]
        self.gui.show_page("comic.qml", override_idle=True)
        self.set_context("XKCD", str(number))
        if speak:
            self.speak(data["alt"], wait=True)
