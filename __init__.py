from mycroft import MycroftSkill, intent_file_handler, intent_handler
import requests
import random
from datetime import datetime, date, timedelta
from mycroft.skills.core import resting_screen_handler
from lingua_franca.format import nice_date
from lingua_franca.parse import extract_number


class XKCDSkill(MycroftSkill):

    @staticmethod
    def get_comic(number):
        return requests.get(
            "http://xkcd.com/" + str(number) + "/info.0.json").json()

    def total_comics(self):
        return self.get_latest()["num"]

    @staticmethod
    def get_latest():
        return requests.get("http://xkcd.com/info.0.json").json()

    def initialize(self):
        self.add_event('skill-xkcd.jarbasskills.home', self.handle_homescreen)
        if not self.settings.get("idle_random"):
            self.settings["idle_random"] = True

    # homescreen
    def handle_homescreen(self, message):
        self.gui.show_url("https://xkcd.com/", override_idle=True)

    # idle screen
    @resting_screen_handler("xkcd")
    def idle(self):
        if not self.settings.get("idle_random"):
            self.update_latest()
            self.gui.show_image(self.settings["imgLink"],
                                fill='PreserveAspectFit')
        else:
            number = random.randint(1, self.total_comics())
            data = self.get_comic(number)
            url = data["img"]
            title = data["safe_title"]
            caption = data["alt"]
            self.speak(caption)
            self.gui.show_image(url,
                                title=title,
                                fill='PreserveAspectFit')

    def update_latest(self):
        try:
            today = datetime.today()
            if not self.settings.get("ts"):
                self.settings["ts"] = (today - timedelta(days=1)).timestamp()
            if today.timestamp() != self.settings["ts"] or \
                    not self.settings.get('imgLink'):
                self.settings["raw_data"] = self.get_latest()
                comic_date = date(day=int(self.settings["raw_data"]["day"]),
                                  month=int(
                                      self.settings["raw_data"]["month"]),
                                  year=int(self.settings["raw_data"]["year"]))
                self.settings["imgLink"] = self.settings["raw_data"]["img"]
                self.settings["title"] = self.settings["raw_data"]["safe_title"]
                self.settings["caption"] = self.settings["raw_data"]["alt"]
                self.settings["date"] = str(comic_date)
                self.settings["spoken_date"] = nice_date(comic_date,
                                                         lang=self.lang)
                self.settings["ts"] = comic_date.timestamp()

        except Exception as e:
            self.log.exception(e)

        self.gui['imgLink'] = self.settings['imgLink']
        self.gui['title'] = self.settings['title']
        self.gui['date'] = self.settings['date']
        self.gui['spoken_date'] = self.settings['spoken_date']
        self.gui['caption'] = self.settings['caption']

    # intents
    @intent_file_handler("total_comics.intent")
    def handle_total_xkcd_intent(self, message):
        self.speak_dialog("xkcd_total_comics",
                          {"number": self.total_comics()})
        self.gui.show_text(str(self.total_comics()) + " comics")

    @intent_file_handler("xkcd_website.intent")
    def handle_website_xkcd_intent(self, message):
        self.handle_homescreen(message)

    @intent_file_handler("latest_xkcd.intent")
    def handle_xkcd_intent(self, message):
        self.update_latest()
        self.speak(self.settings["caption"])
        self.gui.show_image(self.settings["imgLink"],
                            override_idle=120,
                            title=self.settings["title"],
                            fill='PreserveAspectFit')

    @intent_file_handler("xkcd_comic.intent")
    def handle_xkcd_comic_intent(self, message):
        number = extract_number(message.data["utterance"],
                                lang=self.lang,
                                ordinals=True)
        total = self.total_comics()
        if number > total:
            self.speak_dialog("num_error", {"total": total})
            self.gui.show_text(str(total) + " comics")
            return
        data = self.get_comic(number)
        url = data["img"]
        title = data["safe_title"]
        caption = data["alt"]
        self.speak(caption)
        self.gui.show_image(url,
                            override_idle=120,
                            title=title,
                            fill='PreserveAspectFit')

    @intent_file_handler("random_xkcd_comic.intent")
    def handle_xkcd_random_intent(self, message):
        number = random.randint(1, self.total_comics())
        data = self.get_comic(number)
        url = data["img"]
        title = data["safe_title"]
        caption = data["alt"]
        self.speak(caption)
        self.gui.show_image(url,
                            override_idle=120,
                            title=title,
                            fill='PreserveAspectFit')


def create_skill():
    return XKCDSkill()
