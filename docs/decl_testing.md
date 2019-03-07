# REST API Testing Declarative Way: Gabbi Framework over Python Unittest

## Problem Statement

### What's the Idea?

There is a motto among some developers - "Less code is better". Another concept is Devlarative vs Imperative programming style. In a traditional imperative style we tell the machine **how** it should do the task, but in declarative style we just tell **what** we would like to get as a result. Look at SQL - this is a typical example of a declarative way.

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

Gabbi project does exactly this. I strictly advise you to study couple of pages in the documentation: main page and Tests Format section. I just show here one test example of user login REST API endpoint.

### What's next?

Gabbi perfectly suits our idea of declarative testing. But sometimes life is beyond any expectations, unpredictable challenges happen, there is always room for improvement.

Example from a project: I need to test REST APIs where user registers, confirms registration and logs in. Obviously, I need to test this in a single scenario: /confirm-registration endpoint should immediately follow /register. And here is an issue.
Suppose I need to supply registration token from a user mailbox to /confirm-registration. This is a *side action* which I must take strictly in between /register and /confirm-registration and feed the result to confirm registration.

Example above is not the most complicated case we can face with. Suppose we test a case where one user of a "payment system" sends some coins to another. In such scenario, we must check user balances before (via API endpoint), execute transaction, check balances after and compare them. That means we need to store some information somewhere and provide custom routine to compare (this may include calculations with fees, etc).

At the time of this writing, Gabbi has almost no support for the situations described above. This article describes a way how I extended Gabbi functionality, the roadmap of the discussion is:

- overview of the standard unittest invocation procedure and how Gabbi fits into this system;
- `preprocess` and `postprocess` handlers, how do they work;
- passing data between tests. `on behalf of` keyword, when it's needed to "deal cards from two hands".

## Python unittest invocation procedure

Actually Gabbi plugs in into the standard Python Unittest module and uses its infrastructure. It is good idea to outline briefly unittest workflow and see where Gabbi comes into play. This understanding will help us a lot when we move forward. The following figure shows us what happens behind the scenes when you hit `python -m unittest <path.to.module.with.tests>`.
Dashed lines show the belonging of functions (outlined in ellipsises) to certain class entities, solid arrow lines show execution flow.
[figure]

## Custom request and response handlers: `preprocess` and `postprocess`

### Actions needed bebore or after test

In the "What's Next" sectoin of the introduction we discussed the use case "Register and verify registration", which requires our framework to fetch extra data from outside (retrieve a token from user's mailbox) and pass it as parameter to the test that follows. We can go for the token only *after* we made request to /register, although we must be ready with the token *before* we go for /registration-confirm. In the first case we can say, we need to plug-in handler to **postprocess** event; in the second one we need a handler for **preprocess**.

This is nearly the concept same as *middlewares*, implemented in frameworks such Django, Scrapy, Node.js Express and Koa. Middlewares are stacks of routines, each of which may add some data or do whatever actions when an entity passed through the stack. `preprocess` and `postprocess` keywords introduced in test description may contani single routine or a list of them.

test_suite_from_dict test_dict

## Passing data between tests
