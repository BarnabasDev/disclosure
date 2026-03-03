from otree.api import *
import random

doc = """
Advisor session: Advisors observe cap color and premium(s) for advice.
"""


class C(BaseConstants):
    NAME_IN_URL = 'md_advisor'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    CAP_COLORS = ['brown', 'black']
    ADVISOR_ROLE = 'Advisor'
    FIXED_ADVISOR_WAGE = 10
    FIXED_CLIENT_WAGE = 10
    PREMIUM_BROWN = 4
    PREMIUM_BLACK = 4
    CLIENT_CORRECT_ADDITIONAL = 4
    CLIENT_WRONG_DEDUCTION = 4
    CLIENT_CORRECT_TOTAL = FIXED_CLIENT_WAGE + CLIENT_CORRECT_ADDITIONAL
    CLIENT_WRONG_TOTAL = FIXED_CLIENT_WAGE - CLIENT_WRONG_DEDUCTION
    BROWN_SUGGESTED_FOLLOWED_TOTAL = FIXED_ADVISOR_WAGE + PREMIUM_BROWN
    BLACK_SUGGESTED_FOLLOWED_TOTAL = FIXED_ADVISOR_WAGE + PREMIUM_BLACK
    POINTS_CONVERSION_RATE = '20 points = $1'

    # Correct answers for comprehension questions
    # Page 1 – Instructions
    COMP1_CORRECT = {
        'q1_answer': 'b',  # BROWN or BLACK
        'q2_answer': 'a',  # Only participant A
        'q3_answer': 'c',  # BROWN or BLACK
        'q4_answer': 'b',  # FOLLOW or ABSTAIN
    }
    # Page 2 – Points
    COMP2_CORRECT = {
        'q5_answer': 'b',  # The color that may give participant A additional points
        'q6_answer': 'd',  # Both participants
        'q7_answer': 'c',  # If A chooses bonus color and B chooses FOLLOW
        'q8_answer': 'd',  # 0
        'q9_answer': 'b',  # If A chooses the color they observed and B chooses FOLLOW
    }




class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent = models.BooleanField(blank=True)
    cap_color = models.StringField()
    payment = models.CurrencyField()
    advisor_suggestion = models.StringField(
        choices=['brown', 'black'],
        label="Which color do you choose?"
    )
    has_premium_brown = models.BooleanField()
    has_premium_black = models.BooleanField()

    # ── Comprehension page 1 – Instructions ──────────────────────────
    # blank=True prevents oTree's server-side empty-value error;
    # JS enforces correct answers before submission is allowed.
    q1_answer = models.StringField(blank=True)  # cap color
    q2_answer = models.StringField(blank=True)  # who observes
    q3_answer = models.StringField(blank=True)  # A's choice
    q4_answer = models.StringField(blank=True)  # B's choice

    # ── Comprehension page 2 – Points ────────────────────────────────
    q5_answer = models.StringField(blank=True)  # bonus color definition
    q6_answer = models.StringField(blank=True)  # who knows bonus color
    q7_answer = models.StringField(blank=True)  # when A gets bonus points
    q8_answer = models.StringField(blank=True)  # A's points if B abstains
    q9_answer = models.StringField(blank=True)  # when B gets 4 points

    # Track how many attempts each page required
    comp1_attempts = models.IntegerField(initial=0)
    comp2_attempts = models.IntegerField(initial=0)


def creating_session(subsession):
    for player in subsession.get_players():
        player.cap_color = random.choice(C.CAP_COLORS)
        player.has_premium_brown = False
        player.has_premium_black = True


# --------------------------------------------------------------------
# ----------------------------- Pages --------------------------------
# --------------------------------------------------------------------

class Consent(Page):
    form_model = 'player'
    form_fields = ['consent']

    @staticmethod
    def error_message(player, values):
        if not values.get('consent'):
            return {'consent': "You must agree to the terms and conditions to continue."}

class Intro1(Page):
    pass


class Intro2(Page):
    pass


class Intro3(Page):
    pass


class Comprehension1(Page):
    form_model = 'player'
    form_fields = ['q1_answer', 'q2_answer', 'q3_answer', 'q4_answer']

    @staticmethod
    def error_message(player, values):
        player.comp1_attempts += 1
        wrong = [f for f, correct in C.COMP1_CORRECT.items() if values.get(f) != correct]
        if wrong:
            return 'One or more answers are incorrect. Please review and try again.'


class Comprehension2(Page):
    form_model = 'player'
    form_fields = ['q5_answer', 'q6_answer', 'q7_answer', 'q8_answer', 'q9_answer']

    @staticmethod
    def error_message(player, values):
        player.comp2_attempts += 1
        wrong = [f for f, correct in C.COMP2_CORRECT.items() if values.get(f) != correct]
        if wrong:
            return 'One or more answers are incorrect. Please review and try again.'


class AdvisorPage(Page):
    form_model = 'player'
    form_fields = ['advisor_suggestion']

class Results(Page):
    pass

class redirect(Page):
    @staticmethod
    def js_vars(player):
        return dict(
            completionlink=
            player.subsession.session.config['completionlink']
        )

# --------------------------------------------------------------------
# ----------------------- Page Sequence -------------------------------
# --------------------------------------------------------------------
page_sequence = [
    Consent,
    Intro1,
    Intro2,
    Intro3,
    Comprehension1,
    Comprehension2,
    AdvisorPage,
    Results,
    redirect,
]