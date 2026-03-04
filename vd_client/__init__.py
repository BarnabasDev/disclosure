from otree.api import *
import csv
from pathlib import Path
import random

doc = """
Client session (voluntary disclosure): Client observes the advisor's suggestion,
possibly the bonus color information (if disclosed), and decides whether to follow.
"""


class C(BaseConstants):
    NAME_IN_URL = 'vd_client'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    CAP_COLORS = ['brown', 'black']
    CLIENT_ROLE = 'Client'
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
        'q6_answer': 'd',  # Participant A, and participant B if A discloses it
        'q7_answer': 'c',  # If A chooses bonus color and B chooses FOLLOW
        'q8_answer': 'd',  # 0
        'q9_answer': 'b',  # If A chooses the color they observed and B chooses FOLLOW
    }

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    def set_payoffs(self):
        for p in self.get_players():
            p.set_client_payoff()


class Player(BasePlayer):
    consent = models.BooleanField(blank=True)
    advisor_code = models.StringField()
    cap_color = models.StringField()
    advisor_choice = models.StringField()
    advisor_has_premium_brown = models.BooleanField()
    advisor_has_premium_black = models.BooleanField()
    advisor_disclose_bonus = models.BooleanField()  # Single disclosure variable
    # true share from CSV (between 0 and 1)
    true_share_advisors = models.FloatField(initial=0)
    # bonus belief payment
    belief_bonus = models.IntegerField(initial=0)

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

    # client choice
    client_decision = models.StringField(
        choices=['follow', 'abstain'],
        label="What do you want to do?"
    )

    # client belief: did advisor tell the true color?
    belief_advisor_truth = models.IntegerField(min=0, max=100)

    payment = models.CurrencyField()

    def set_client_payoff(self):
        payoff = C.FIXED_CLIENT_WAGE
        if self.client_decision == 'follow':
            if self.advisor_choice == self.cap_color:
                payoff += C.CLIENT_CORRECT_ADDITIONAL
            else:
                payoff -= C.CLIENT_WRONG_DEDUCTION
        self.payment = payoff


def creating_session(subsession):
    file_path = Path(__file__).parent / 'vd_advisor_raw.csv'

    with open(file_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_advisors = list(reader)

    # Filter: only advisors who disclosed their bonus
    disclosed = [a for a in all_advisors if int(a['advisor_disclose_bonus']) == 1]

    # Split into two pools by cap color
    brown_pool = [a for a in disclosed if a['cap_color'] == 'brown']
    black_pool = [a for a in disclosed if a['cap_color'] == 'black']

    if not brown_pool:
        raise ValueError("No disclosed advisors with cap_color='brown' found in CSV!")
    if not black_pool:
        raise ValueError("No disclosed advisors with cap_color='black' found in CSV!")

    players = subsession.get_players()
    n = len(players)

    # Build a balanced assignment for each color pool separately,
    # then interleave them 50-50 (brown, black, brown, black, ...)
    def balanced_assignments(pool, count):
        if count < len(pool):
            raise ValueError(
                f"Not enough clients ({count}) to match all {len(pool)} advisors at least once!"
            )

        # Start with one guaranteed round of every advisor
        assignment = pool.copy()
        random.shuffle(assignment)

        # Fill the remainder with balanced batches
        while len(assignment) < count:
            batch = pool.copy()
            random.shuffle(batch)
            assignment.extend(batch)

        assignment = assignment[:count]
        random.shuffle(assignment)
        return assignment

    n_brown = n // 2
    n_black = n - n_brown  # handles odd numbers by giving black one extra

    brown_assignments = balanced_assignments(brown_pool, n_brown)
    black_assignments = balanced_assignments(black_pool, n_black)

    # Interleave and shuffle so color isn't ordered in the player list
    assignment = brown_assignments + black_assignments
    random.shuffle(assignment)

    for p, advisor in zip(players, assignment):
        p.advisor_code = advisor['advisor_code']
        p.cap_color = str(advisor['cap_color'])
        p.advisor_choice = str(advisor['advisor_choice'])
        p.advisor_has_premium_brown = int(advisor['advisor_has_premium_brown'])
        p.advisor_has_premium_black = int(advisor['advisor_has_premium_black'])
        p.advisor_disclose_bonus = int(advisor['advisor_disclose_bonus'])
        p.true_share_advisors = float(advisor['share_chose_observed'])


# PAGES
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


class ClientPage(Page):
    form_model = 'player'
    form_fields = ['client_decision']

    def vars_for_template(player):
        return dict(
            cap_color=player.cap_color,
            advisor_choice=player.advisor_choice,
            advisor_has_premium_brown=player.advisor_has_premium_brown,
            advisor_has_premium_black=player.advisor_has_premium_black,
            advisor_disclose_bonus=player.advisor_disclose_bonus,
        )


class ClientBeliefPage(Page):
    form_model = 'player'
    form_fields = ['belief_advisor_truth']

    def before_next_page(player, timeout_happened):
        player.set_client_payoff()

        if player.true_share_advisors is None:
            raise ValueError("true_share_advisors was not properly assigned in creating_session()")

        # Convert true share (0–1) into 0–100 scale
        true_percentage = round(player.true_share_advisors * 100)

        # Check if guess is within ±5
        if abs(player.belief_advisor_truth - true_percentage) <= 5:
            player.belief_bonus = 2
        else:
            player.belief_bonus = 0

        # Add bonus to payment
        player.payment += player.belief_bonus

class Results(Page):
    def vars_for_template(player):
        points = int(player.payment)
        earnings = float(player.payment) / 20
        final_payment = 1 + float(player.payment) / 20
        return dict(
            final_points=player.payment,
            advisor_choice=player.advisor_choice,
            cap_color=player.cap_color,
            points_balance=points,
            final_earnings=f"{earnings:.2f}",
            belief_bonus=player.belief_bonus,
            final_payment=final_payment,
        )

class redirect(Page):
    @staticmethod
    def js_vars(player):
        return dict(
            completionlink=
            player.subsession.session.config['completionlink']
        )

page_sequence = [
    Consent,
    Intro1,
    Intro2,
    Intro3,
    Comprehension1,
    Comprehension2,
    ClientPage,
    ClientBeliefPage,
    Results,
    redirect
]