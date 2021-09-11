from django.contrib import messages
from django.core.mail import mail_admins, send_mass_mail
from django.db.models import Count
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView

from accounts.models import EmailUser
from home import models
from home.views import get_planning_context
from site_settings.models import Colors, SiteSettings
from shared.views import CSVWriteView, SuperuserRequiredMixin

# ==============================
# Main Admin views
# ==============================


class AdminView(SuperuserRequiredMixin, TemplateView):
	template_name = "admin.html"

	def get_metrics(self):
		registered = models.InterludesParticipant.objects.filter(is_registered = True)
		acts = models.InterludesActivity.objects.all()
		slots_in = models.InterludesSlot.objects.all()
		wishes = models.InterludesActivityChoices.objects.filter(participant__is_registered=True)
		class metrics:
			participants = registered.count()
			ulm = registered.filter(school=models.InterludesParticipant.ENS.ENS_ULM).count()
			lyon = registered.filter(school=models.InterludesParticipant.ENS.ENS_LYON).count()
			rennes = registered.filter(school=models.InterludesParticipant.ENS.ENS_RENNES).count()
			saclay = registered.filter(school=models.InterludesParticipant.ENS.ENS_CACHAN).count()
			non_registered = EmailUser.objects.filter(is_active=True).count() - participants
			# mugs = registered.filter(mug=True).count()
			sleeps = registered.filter(sleeps=True).count()

			meal1 = registered.filter(meal_friday_evening=True).count()
			meal2 = registered.filter(meal_saturday_morning=True).count()
			meal3 = registered.filter(meal_saturday_midday=True).count()
			meal4 = registered.filter(meal_saturday_evening=True).count()
			meal5 = registered.filter(meal_sunday_morning=True).count()
			meal6 = registered.filter(meal_sunday_midday=True).count()
			meals = meal1 + meal2 + meal3 + meal4 + meal5 + meal6

			activites = acts.count()
			displayed = acts.filter(display=True).count()
			act_ins = acts.filter(display=True, must_subscribe=True).count()
			communicate = acts.filter(communicate_participants=True).count()
			st_present = acts.filter(display=True, status=models.InterludesActivity.Status.PRESENT).count()
			st_distant = acts.filter(display=True, status=models.InterludesActivity.Status.DISTANT).count()
			st_both = acts.filter(display=True, status=models.InterludesActivity.Status.BOTH).count()

			slots = slots_in.count()
			true_ins = slots_in.filter(subscribing_open=True).count()
			wish = wishes.count()
			granted = wishes.filter(accepted=True).count()
			malformed = models.InterludesActivityChoices.objects.filter(slot__subscribing_open=False).count()

		return metrics

	def validate_activity_participant_nb(self):
		""" Vérifie que le nombre de participant inscrit
		à chaque activité est compris entre le min et le max"""
		slots = models.InterludesSlot.objects.filter(subscribing_open=True)
		min_fails = ""
		max_fails = ""
		for slot in slots:
			total = models.InterludesActivityChoices.objects.filter(
				slot=slot, accepted=True, participant__is_registered=True
			).aggregate(total=Count("id"))["total"]
			max = slot.activity.max_participants
			min = slot.activity.min_participants
			if max != 0 and max < total:
				max_fails += "<br> &bullet;&ensp;{}: {} inscrits (maximum {})".format(
					slot, total, max
				)
			if min > total:
				min_fails += "<br> &bullet;&ensp;{}: {} inscrits (minimum {})".format(
					slot, total, min
				)
		message = ""
		if min_fails:
			message += '<li class="error">Activités en sous-effectif : {}</li>'.format(min_fails)
		else:
			message += '<li class="success">Aucune activité en sous-effectif</li>'
		if max_fails:
			message += '<li class="error">Activités en sur-effectif : {}</li>'.format(max_fails)
		else:
			message += '<li class="success">Aucune activité en sur-effectif</li>'
		return message

	def validate_activity_conflicts(self):
		"""Vérifie que personne n'est inscrit à des activités simultanées"""
		slots = models.InterludesSlot.objects.filter(subscribing_open=True)
		conflicts = []
		for i, slot_1 in enumerate(slots):
			for slot_2 in slots[i+1:]:
				if slot_1.conflicts(slot_2):
					conflicts.append((slot_1, slot_2))
		base_qs = models.InterludesActivityChoices.objects.filter(
			accepted=True, participant__is_registered=True
		)
		errors = ""
		for slot_1, slot_2 in conflicts:
			participants_1 = {x.participant for x in base_qs.filter(slot=slot_1)}
			participants_2 = {x.participant for x in base_qs.filter(slot=slot_2)}
			intersection = participants_1.intersection(participants_2)
			if intersection:
				errors += '<br> &bullet;&ensp; {} participe à la fois à "{}" et à "{}"'.format(
					", ".join(str(x) for x in intersection), slot_1, slot_2
				)

		if errors:
			return '<li class="error">Des participants ont plusieurs activités au même moment :{}</li>'.format(
				errors
			)
		return '<li class="success">Aucun inscrit à plusieurs activités simultanées</li>'

	def validate_slot_less(self):
		"""verifie que toutes les activité demandant une liste de participant ont un créneaux"""
		activities = models.InterludesActivity.objects.filter(communicate_participants=True)
		errors = ""
		for activity in activities:
			count = models.InterludesSlot.objects.filter(activity=activity).count()
			if count == 0:
				errors += "<br> &bullet;&ensp; {}".format(activity.title)
		if errors:
			return '<li class="error">Certaines activités demandant une liste de participants n\'ont pas de créneaux :{}<br>Leurs orgas vont recevoir un mail inutile.</li>'.format(
				errors
			)
		return '<li class="success">Toutes les activités demandant une liste de participants ont au moins un créneau</li>'

	def validate_multiple_similar_inscription(self):
		"""verifie que personne n'est inscrit à la même activité plusieurs fois"""
		slots = models.InterludesSlot.objects.filter(subscribing_open=True)
		conflicts = []
		for i, slot_1 in enumerate(slots):
			for slot_2 in slots[i+1:]:
				if slot_1.activity == slot_2.activity:
					conflicts.append((slot_1, slot_2))
		base_qs = models.InterludesActivityChoices.objects.filter(
			accepted=True, participant__is_registered=True
		)
		errors = ""
		for slot_1, slot_2 in conflicts:
			participants_1 = {x.participant for x in base_qs.filter(slot=slot_1)}
			participants_2 = {x.participant for x in base_qs.filter(slot=slot_2)}
			intersection = participants_1.intersection(participants_2)
			if intersection:
				errors += '<br> &bullet;&ensp; {} inscrit aux créneaux "{}" et  "{}" de l\'activité "{}"'.format(
					", ".join(str(x) for x in intersection), slot_1, slot_2, slot_1.activity
				)

		if errors:
			return '<li class="error">Des participants sont inscrits plusieurs fois à la même activité :{}</li>'.format(
				errors
			)
		return '<li class="success">Aucun inscrit plusieurs fois à une même activité</li>'

	def validate_activity_allocation(self):
		settings = SiteSettings.load()
		validations = '<ul class="messagelist">'

		# validate global settings
		if not settings.inscriptions_open:
			validations += '<li class="success">Les inscriptions sont fermées</li>'
		else:
			validations += '<li class="error">Les inscriptions sont encores ouvertes</li>'
		if settings.activities_allocated:
			validations += '<li class="success">La répartition est marquée comme effectuée</li>'
		else:
			validations += '<li class="error">La répartition n\'est pas marquée comme effectuée</li>'

		# longer validations
		validations += self.validate_activity_participant_nb()
		validations += self.validate_activity_conflicts()
		validations += self.validate_multiple_similar_inscription()
		validations += self.validate_slot_less()

		if settings.discord_link:
			validations += '<li class="success">Le lien du discord est renseigné</li>'
		else:
			validations += '<li class="error">Le lien du discord n\'est pas renseigné</li>'

		validations += '</ul>'

		user_email_nb = models.InterludesParticipant.objects.filter(is_registered=True).count()
		orga_email_nb = models.InterludesActivity.objects.filter(
			communicate_participants=True
		).count()

		return {
			"validations": validations,
			"user_email_nb": user_email_nb,
			"orga_email_nb": orga_email_nb,
			"validation_errors": '<li class="error">' in validations
		}

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context["metrics"] = self.get_metrics()
		context.update(get_planning_context())
		context.update(self.validate_activity_allocation())
		return context


# ==============================
# DB Export Views
# ==============================


class ExportActivities(SuperuserRequiredMixin, CSVWriteView):
	filename = "activites_interludes"
	model = models.InterludesActivity

class ExportSlots(SuperuserRequiredMixin, CSVWriteView):
	filename = "créneaux_interludes"
	headers = [
		"Titre", "Début", "Salle",
		"Ouverte aux inscriptions", "Affichée sur le planning",
		"Couleur", "Durée", "Durée activité",
	]

	def get_rows(self):
		slots = models.InterludesSlot.objects.all()
		rows = []
		for slot in slots:
			rows.append([
				str(slot), slot.start, slot.room,
				slot.subscribing_open, slot.on_planning,
				Colors(slot.color).name, slot.duration, slot.activity.duration	,
			])
		return rows

class ExportParticipants(SuperuserRequiredMixin, CSVWriteView):
	filename = "participants_interludes"
	headers = [
		"id", "mail", "prénom", "nom", "ENS", "Dors sur place", #"Tasse",
		"Repas vendredi", "Repas S matin", "Repas S midi", "Repas S soir",
		"Repas D matin", "Repas D soir"
	]
	def get_rows(self):
		profiles = models.InterludesParticipant.objects.filter(is_registered=True).all()
		rows = []
		for profile in profiles:
			rows.append([
				profile.user.id,
				profile.user.email,
				profile.user.first_name,
				profile.user.last_name,
				profile.school,
				profile.sleeps,
				# profile.mug,
				profile.meal_friday_evening,
				profile.meal_saturday_morning,
				profile.meal_saturday_midday,
				profile.meal_saturday_evening,
				profile.meal_sunday_morning,
				profile.meal_sunday_midday,
			])
		return rows

class ExportActivityChoices(SuperuserRequiredMixin, CSVWriteView):
	filename = "choix_activite_interludes"
	model = models.InterludesActivityChoices
	headers = ["id_participant", "nom_participant", "mail_participant", "priorité", "obtenu", "nom_créneau", "id_créneau"]

	def get_rows(self):
		activities = models.InterludesActivityChoices.objects.all()
		rows = []
		for act in activities:
			if act.participant.is_registered:
				rows.append([
					act.participant.id, str(act.participant), act.participant.user.email, act.priority,
					act.accepted, str(act.slot), act.slot.id
				])
		return rows


# ==============================
# Send email views
# ==============================


class SendEmailBase(SuperuserRequiredMixin, RedirectView):
	"""Classe abstraite pour l'envoie d'un groupe d'emails"""
	pattern_name = "admin_pages:index"
	from_address = None

	def send_emails(self):
		raise NotImplementedError("{}.send_emails isn't implemented".format(self.__class__.__name__))

	def get_redirect_url(self, *args, **kwargs):
		settings = SiteSettings.load()
		if settings.allow_mass_mail:
			self.send_emails()
		else:
			messages.error(self.request, "L'envoi de mail de masse est désactivé dans les réglages")
		return reverse(self.pattern_name)

class SendUserEmail(SendEmailBase):
	"""Envoie aux utilisateurs leur repartition d'activité"""

	def get_emails(self):
		"""genere les mails a envoyer"""
		participants = models.InterludesParticipant.objects.filter(is_registered=True)
		emails = []
		settings = SiteSettings.load()
		for participant in participants:
			my_choices = models.InterludesActivityChoices.objects.filter(participant=participant)
			message = render_to_string("email/user.html", {
				"user": participant.user,
				"settings": settings,
				"requested_activities_nb": my_choices.count(),
				"my_choices": my_choices.filter(accepted=True),
			})
			emails.append((
				"[interludes] Vos activités", # subject
				message,
				self.from_address, # From:
				[participant.user.email], # To:
			))
		return emails

	def send_emails(self):
		settings = SiteSettings.load()
		if settings.user_notified:
			messages.error(self.request, "Les participants ont déjà reçu un mail annonçant la répartition. Modifiez les réglages pour en envoyer un autre")
			return
		settings.user_notified = True
		settings.save()
		emails = self.get_emails()

		nb_sent = send_mass_mail(emails, fail_silently=False)
		mail_admins(
			"Emails de répartition envoyés aux participants",
			"Les participants ont reçu un mail leur communiquant la répartition des activités\n"
			"Nombre total de mail envoyés: {}\n\n"
			"-- Site Interludes (mail généré automatiquement".format(nb_sent)
		)
		messages.success(self.request, "{} mails envoyés aux utilisateurs".format(nb_sent))

class SendOrgaEmail(SendEmailBase):
	"""
	Envoie aux organisateur leur communiquant les nom/mail des inscrits
	à leurs activités
	"""

	def get_emails(self):
		"""genere les mails a envoyer"""
		activities = models.InterludesActivity.objects.filter(communicate_participants=True)
		emails = []
		settings = SiteSettings.load()
		for activity in activities:
			slots = models.InterludesSlot.objects.filter(activity=activity)
			message = render_to_string("email/orga.html", {
				"activity": activity,
				"settings": settings,
				"slots": slots,
			})
			emails.append((
				"[interludes] Liste d'inscrits à votre activité {}".format(activity.title), # subject
				message,
				self.from_address, # From:
				[activity.host_email] # To:
			))
		return emails

	def send_emails(self):
		settings = SiteSettings.load()
		if settings.orga_notified:
			messages.error(self.request, "Les orgas ont déjà reçu un mail avec leur listes d'inscrits. Modifiez les réglages pour en envoyer un autre")
			return
		settings.orga_notified = True
		settings.save()
		emails = self.get_emails()

		nb_sent = send_mass_mail(emails, fail_silently=False)
		mail_admins(
			"Listes d'inscrits envoyés aux orgas",
			"Les mails communiquant aux organisateurs leur listes d'inscrit ont été envoyés\n"
			"Nombre total de mail envoyés: {}\n\n"
			"-- Site Interludes (mail généré automatiquement".format(nb_sent)
		)
		messages.success(self.request, "{} mails envoyés aux orgas".format(nb_sent))