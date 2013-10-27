from celery import Celery
from sqlalchemy.orm import scoped_session

from settings import Config
config = Config()

from models import Reservation, Flight, FlightLeg, FlightLegLocation
from db import Database
from sw_checkin_email import *

celery = Celery('tasks')
celery.config_from_object('celery_config')

@celery.task(default_retry_delay=config["RETRY_INTERVAL"], max_retries=config["MAX_RETRIES"])
def test_celery(flight_id):
  try:
    db = Database('southwest-checkin.db')
    flight = session.query(Flight).get(flight_id)
    return "Found flight %s" % flight.id
  except Exception, exc:
    raise test_celery.retry(exc=exc)

@celery.task(default_retry_delay=config["RETRY_INTERVAL"], max_retries=config["MAX_RETRIES"])
def check_in_flight(reservation_id, flight_id):
  flight = db.Session.query(Flight).get(flight_id)
  if flight.success:
    print "Skipping flight %d. Already checked in at %s" % (flight_id, flight.position)
    return

  reservation = db.Session.query(Reservation).get(reservation_id)

  (position, boarding_pass) = getBoardingPass(reservation)

  if position:
    return check_in_success(reservation, flight, boarding_pass, position)
    db.Session.remove()
  else:
    print 'FAILURE. Scheduling another try in %d seconds' % config["RETRY_INTERVAL"]
    db.Session.remove()
    raise check_in_flight.retry(reservation_id, flight_id)