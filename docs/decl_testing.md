# REST API Testing Declarative Way: Gabbi Framework over Python Unittest

Yury Danilin `yuvede@gmail.com`

## Problem Statement

### What's the Idea?

There is a motto among some developers - "Less code is better". Another concept is *Declarative* vs *Imperative* programming style. In a traditional imperative style we tell the machine **how** it should do the task, but in declarative style we just tell **what** we would like to get as a result. Look at SQL - this is a perfect example of a declarative way.

I don't want to write too much code for tests. Don't think I'm lazy - I would like to describe tests declarative way to make them read easy. The benefit for this is evident - such declarations are *self-documenting* and clear. That means everybody can easily get into the context even after some time passed after.

Okay, coming back to API testing: I want do declare tests in a text file to clearly see:

- to what endpoint, whith which method, headers and payload I want to make a request;
- what I want to test in responses.

Due to my opinion, YAML is the best format to describe structured data:

- lists and dictionaries are without annoying braces;
- can even declare empty lists and dicts;
- has *file variables*, which are usefull to declare repititive data spreaded along the file.

Are the any existing Python libraries which can do described above?

### The Solution is: Gabbi

[Gabbi project] does exactly this. I strictly advise you to study for the first time just couple of pages in the documentation: [main page] and [Tests Format] section. I just show here one test example of user login REST API endpoint.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.yaml .numberLines}
# file variables are convenient in case we reference data several times
# to use values elsewhere, start *variable_name with asterisk 
username: &username <my user name>
password: &password <my user password>

tests:
  - name: user login
    desc: User login
    POST: /login
    request_headers:
        content-type: application/json
    data:
        email_or_username: *username
        password: *password
    status: 200
    response_headers:
        Content-Type: application/json
    response_json_paths:
        $.data.user_type: Buyer
        $.message: /^Logged in successfully/
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Looks good! Self-explaining, almost no additional description needed. I will comment only last two lines: Gabbi has good enough support for accessing JSON members via jsonpath, plus allows regular expressions in test conditions - I use them constantly to check messages like this to avoid punctuation issues at the end of messages (there is an "!" at the end but next time devs may forget to add it).

### What's next?

Gabbi perfectly suits our idea of declarative testing. But sometimes life is beyond any expectations, unpredictable challenges happen, there is always room for improvement.

Example from a project: I need to test REST APIs where user registers, confirms registration and logs in. Obviously, I need to test this in a single scenario: `/confirm-registration` endpoint should immediately follow `/register`. And here is an issue.
Suppose I need to supply registration token from a user mailbox to `/confirm-registration`. This is a *side action* which I must take strictly in between `/register` and `/confirm-registration` and feed the result to confirm registration.

Example above is not the most complicated case we can face with. Suppose we test a case where one user of a "payment system" sends some coins to another. In such scenario, we must check user balances before (via API endpoint), execute transaction, check balances after and compare them. That means we need to store some information somewhere and provide custom routine to compare (this may include calculations with fees, etc).

At the time of this writing, Gabbi has almost no support for the situations described above. This article describes a way how I extended Gabbi functionality, the roadmap of the discussion is:

- overview of the standard unittest invocation procedure and how Gabbi fits into this system;
- `preprocess` and `postprocess` handlers, how do they work;
- passing data between tests. `on behalf of` keyword, when it's needed to "deal cards from two hands".

## Python unittest invocation procedure

Actually Gabbi plugs in into the standard Python [Unittest] module and uses its infrastructure. It is good idea to outline briefly unittest workflow and see where Gabbi comes into play. This understanding will help us a lot when we move forward. The following figure shows us what happens behind the scenes when you hit `python -m unittest <path.to.module.with.tests>`.
Dashed lines show the belonging of functions (outlined in ellipsises) to certain class entities, solid arrow lines show execution flow.

![Standard Python unittest workflow diagram](decl_testing/test_invok_standard.svg){.center}

Now we will show the same picture with emphasis to Gabbi part and some standard components omited.

![Gabbi part workflow diagram](decl_testing/test_invok_gabbi.svg){.center}

## Custom request and response handlers: `preprocess` and `postprocess`

### Actions needed bebore or after test

In the "What's Next" sectoin of the introduction we discussed the use case "Register and verify registration", which requires our framework to fetch extra data from outside (retrieve a token from user's mailbox) and pass it as parameter to the test that follows. We can go for the token only *after* we made request to /register, although we must be ready with the token *before* we go for /registration-confirm. In the first case we can say, we need to plug-in handler to **postprocess** event; in the second one we need a handler for **preprocess**.

This is nearly the concept same as *middlewares*, implemented in frameworks such Django, Scrapy, Node.js Express and Koa. Middlewares are stacks of routines, each of which may add some data or do whatever actions when an entity passed through the stack. `preprocess` and `postprocess` keywords introduced in test description may contain single routine or a list of them.

### Extension mechanism

Earlier we studied a bit the test implementation workflow and saw which parts of Gabbi are responsible for test creation. First, Gabbi loads `yaml` files and make dictionaries from them. Next, it iterates through `tests` list declaration and creates test from every description. Luckly, everything that was declared under each test entry in the list, becomes available in `test.test_data` field of each test.

Finally everything is converted into `HTTPTestCase`, which encapsulates everything needed to make REST API request and test the response. This is exactly the class, where we can find places to insert our `preprocess` and `postprocess` handlers. Namely, we need to methods:

- `_run_test()`, where actually taxiing to runway and taking off are happen;
- `_assert_response()`, where flight debriefing takes place.

I put the following fragment

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.python}
# custom functionality module, explained later
from handlers import invoke_handlers

        # insert preprocess handling here (postprocess in _assert_response)
        if not self.test_data['skip']:
            invoke_handlers(self, 'preprocess')
            # invoke_handlers(self, 'postprocess') for postprocess
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

into these methods in `case.py` file. I'm passing here a reference to the class (`HTTPTestCase`) instance and a string message what to find.

Now we're ready to go for realization. Let's proceed to our custom `handlers.py` module.

Coming back to out sample use case "register - confirm" first we define the necessary functions to retireve confirmation token and to inject it to the test instance. Couple of important points to notice here:

- when we have retrieved token (first procedure), we need to store it somewhere. For that purpose, I introduced special key named `meta` to `test.test_data` field. Just note that, I'll explain this in the following section.
- Gabbi puts all POST request payload data nuder the same named key `test.test_data['data']`. So,the procedure to set the token for request just copies it from our `meta` storage to aircraft's cargo bay under the name (key) REST API endpoint expects.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.python .numberLines}
# postprocessor functions
def retrieve_email_token(test):
    email_token = check_email_for_token()  # whatever procedure
    if email_token:
        test.test_data['meta'].update({'email_token': email_token})
    else:
        print('\nDid not receive a registration token')
        test.test_data['meta'].update({'email_token': 'did not receive'})


# preprocessor functions
def set_email_token(test):
    email_token = test.test_data['meta']['email_token']
    test.test_data['data']['confirm_token'] = email_token


POSTPROCESS = {
    'retrieve_email_token': retrieve_email_token,
    # ... other functions ...
}


PREPROCESS = {
    'set_email_token': set_email_token,
    # ... other functions ...
}


def invoke_handlers(test, pre_or_postprocess):
    func_table = {
        'preprocess': PREPROCESS,
        'postprocess': POSTPROCESS,
    }
    handlers = test.test_data.get(pre_or_postprocess, [])
    actions = handlers if isinstance(handlers, list) else [handlers]
    for action in actions:
        func_table[pre_or_postprocess][action](test)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we define two function tables (dictionaries) for preprocess and postprocess functions respectively.

Finally the main procedure `invoke_handlers()` appears. Using the technique to avoid `if`s, we select an appropriate function table (global one) and use, as [David Beazley] calls it, "sneaky method call" to invoke functions declared at the beginning.

Note that with line xx we allow `preprocess` or `postprocess` keys in yaml files to be a single declarations or functions sequental lists.

## Passing data between tests

### Why May We Need a Custom Test Runner

When discussing `preprocess` or `postprocess` handlers we imply that one type of handlers may be called in one test and another type of handlers in the test *that follows*. This way we need to decide how to transfer our test metadata (stored under `meta` key in `test.test_data`) from one test to another. Several ways may exist for that but, as I decided to make custom reporting as well, I made **custom test runner** and implemented there also custom `TextTestResult` class which inherits [standard unittest] `TestResult`.

From the test invocation workflow diagram you see that `TestCase`'s `run()` metnod calls:

- `startTest()`;
- `stopTest()`;
- `addSuccess()` or `addFailure()` or `addError()`.

That way the test informs us that he is about to start, completed and what was his outcome.
So `startTest()` is a good place to do a metadata transfer needed.

Seems we're lucky again :-). Every test instance provides a reference to the previous test (if such exists) `test.prior`, so we override `startTest()` method to do the job: 

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.python .numberLines}
    def startTest(self, test):
        # transfer tests metadata
        prior_meta = test.prior.test_data.get('meta', {}) if test.prior else {}
        current_meta = test.test_data.get('meta', {})
        current_meta.update(prior_meta)
        test.test_data['meta'] = current_meta
        TestResult.startTest(self, test)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

### Deal Cards from Two Hands

Here I would introduce one more detail on Gabbi functionality - `defaults` section for yaml test definition files. In a nutshell, a dictionary under `defaults` actually *merges* with `test.test_data`. As its name says, `defaults` are for data, applicable to all test within a yaml file. This allows us to adapt to rather complicated test scenarios.

In the introduction we mentioned a scenario where one user of a "payment system" would send some coins to another user within the system. That is the situation where we have to "deal cards from two hands" simultaneously. Let's call our parties "sender" and "receiver". Let us briefly review what data could be necessary for steps of such scenario:

- we check initial balance of **both** sender and receiver. Note that these will be *separate* REST API calls. Thus we need to store account numbers separately for each party and initial balance same way;
- we perform transaction (and probably confirmation, too) *on behalf of* the sender;
- we repeat Step 1 (again two API calls) and this time compare actual balances with initial ones.

Note that for such scheme to work, we need to **organize separate sections** in our `test.test_data['meta']` storage and, as mentioned in step 2, every test must know **on befalf of** whom the test is conducted.

I show here a fragment of yaml file and a code fragment from `handlers.py` to illustrate the approach:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.yaml .numberLines}
defaults:
    ssl: True  # system setting described in Gabbi docs
    meta:
        sender:  # note separate sections for sended and receiver
            name: *sender
            account_number: *account_number
            balance_before: 0  # not necessary to declare here but shown
                               # for illustrative purpose
        receiver:
            name: *receiver
            account_number: *account_number
            balance_before: 0

tests:
  - test one
    # ... misc lines ....
    POST /transactions
    on_behalf_of: sender  # party name must be the same as in "defaults" declaration!
    # ... misc lines ....
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The declaration under `defaults` will be converted into a regulat Python dictionary. Now we must adapt our code in `handlers.py` to be flexible to handle situations whether `meta` section in `defaults` divided into two parties or not:

As an example of the Pyhton code I'll provide here a procedure which assumes we store 2FA token for (for example) sender, generate 2FA TOTP-password and write it to payload section sent to API endpoint:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.python .numberLines}
def set_tfa_totp(test):
    tdata = test.test_data
    on_behalf_of = tdata.get('on_behalf_of')  # remember we provided `on_behalf_of`
                                              # keyword in a test declaration
    # here we added flexibility to handle both single-role scenarion ('meta' is
    # not divided) and two-role scenarions ('meta' is divided)
    from_where = tdata['meta'][on_behalf_of] if on_behalf_of else tdata['meta']
    tfa_secret = from_where.get('tfa_secret')
    # write standalone generation routine output to POST payload data
    test.test_data['data']['2fa_password'] = get_totp_token(tfa_secret)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

## Afterword

Gabbi framework itself is very useful in REST API testing. I advise you to investigate the [documentation] deeper to discover its powerful capabilities such as:

- JSONPath response data evaluator. Note that expected test JSONs to compare with can be loaded from separate files.
- magical variables that can be used to make reference to the state of a current test, the one just prior or any test prior to the current one. The variables are replaced with real values during test processing. Sometimes these references provided by Gabby may replace our keyword `meta` approach. I was aware of this built-in functionality when introduced `meta` keyword and now use these two approaches interchangebly, which one creates less amount of code.

I do not consider adaptations made here as final and only right ones like cast in bronze, but would be glad if you find this helpful.

### Funny notes

Gabbi is jealous to keys supplied in test declaration in yamls and tries to throw an error when it sees keys not approved by him. In order to make him trust to our extension keys like `on_behalf_of`, `preprocess` or `postprocess`, we must find `BASE_TEST` global dictionary at hte beginnig of `case.py` file and add our new keywords into that dict.

I do not remember the reason, but I had to alter procedure `test_update()` in `suitemaker.py` file this way (some code was commented):

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ {.yaml .numberLines}
def test_update(orig_dict, new_dict):
    """Modify test in place to update with new data."""
    for key, val in new_dict.items():
        # if key == 'data':
        #     orig_dict[key] = val
        # elif isinstance(val, dict):
        #     orig_dict[key].update(val)
        if isinstance(val, list):
            orig_dict[key] = orig_dict.get(key, []) + val
        else:
            orig_dict[key] = val
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[Gabbi project]: https://github.com/cdent/gabbi
[main page]: https://gabbi.readthedocs.io/en/latest/
[Tests Format]: https://gabbi.readthedocs.io/en/latest/format.html
[Unittest]: https://docs.python.org/3.6/library/unittest.html
[David Beazley]: https://pyvideo.org/python-brasil-2015/keynote-david-beazley-topics-of-interest-python-asyncio.html
[standard unittest]: https://docs.python.org/3/library/unittest.html#unittest.TestResult
[documentation]: https://gabbi.readthedocs.io/en/latest/
