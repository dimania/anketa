# **Telegram bot for conducting surveys**

This Telegram bot is designed for conducting surveys or questionnaires.
What it can do:

* Load questions from an Excel spreadsheet
* View statistics on survey completion
* Assign/remove bot administrators
* Obtain a report of survey results in Excel format
* Users receive their own questionnaire results in PDF format
* Upload custom logos for the survey

The following Excel spreadsheet format for questions is supported:

The first column (A) – **type** – can take the following values:

**header**\
  (Column B): any text, displayed as a message to the user once at the very beginning.\
  (Column C): image file name; if filled, the text will be displayed as a caption for the image.\
  remaining columns are ignored.

**text**\
  (Column B): any text, displayed as a message to the user. Does not imply any action from the user.

**simple**\
  (Column B): any text, displayed as a question. Expects the user to input and send a message.\
  remaining columns are ignored.

**onlyone**\
  (Columns B-Z..): any text, displayed as a menu of buttons. Single choice allowed.

**select**\
  (Columns B-Z..): any text, displayed as a menu of buttons. Multiple choices allowed.

**footer**\
  (Column B): any text, displayed as a message to the user once at the end, after the last question.\
  (Column C): image file name; if filled, the text will be displayed as a caption for the image.\
  remaining columns are ignored.

**report**\
  (Column B): any text, displayed as a title in the user’s report when generating the PDF.\
  (Column C): image file name; if filled, it is displayed as a logo in the user’s report when generating the PDF.\
  remaining columns are ignored.

**Example**

|    A    |                     B                      |         C          |      D       |          E          |
| :-----: | :----------------------------------------: | :----------------: | :----------: | :-----------------: |
| header  |       Please answer a few questions:       |     logo.jpeg      |              |                     |
|  text   |                First block                 |                    |              |                     |
| simple  |               First and last name          |                    |              |                     |
| onlyone |              How old are you?              |       15-25        |    26-50     |       51-100        |
|  text   |                Second block                |                    |              |                     |
| select  |           What matters most to you now?    |   Relieve pain     | Improve sleep| Reduce anxiety      |
| footer  | Congratulations! You have answered all questions. | congratulation.jpg |              |                     |
| report  |                 Questionnaire              |     logo.jpeg      |              |                     |

**WARNING! When loading new questions, current questions and answers will be deleted!**

* After answering the last question, the user receives their personal report in PDF format.

* The administrator can export the results for all users in Excel format.