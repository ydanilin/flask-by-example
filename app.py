import os
import operator
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from rq import Queue
from rq.job import Job
from worker import conn
from scraping import count_and_save_words


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

q = Queue(connection=conn)

from models import Result


@app.route('/', methods=['GET', 'POST'])
def index():
    results = {}
    if request.method == "POST":
        # get url that the person has entered
        url = request.form['url']
        if 'http' not in url[:7]:
            url = 'http://' + url
        job = q.enqueue_call(
            func=count_and_save_words, args=(url, ), result_ttl=5000
        )
        print(job.get_id())

    return render_template('index.html', results=results)


@app.route("/results/<job_key>", methods=['GET'])
def get_results(job_key):
    errors = []
    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        # save the results
        url, raw_word_count, no_stop_words_count = job.result
        try:
            result_record = Result(
                url=url,
                result_all=raw_word_count,
                result_no_stop_words=no_stop_words_count
            )
            db.session.add(result_record)
            db.session.commit()
            # return result.id
        except:
            errors.append("Unable to add item to database.")
            return {"error": errors}
        result = Result.query.filter_by(id=result_record.id).first()
        results = sorted(
            result.result_no_stop_words.items(),
            key=operator.itemgetter(1),
            reverse=True
        )[:10]
        return jsonify(results)
    else:
        return "Nay!", 202


if __name__ == '__main__':
    app.run()
