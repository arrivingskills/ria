# Creating Content on a Page

# see also
<https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates>

All page content goes inside `{% block content %}...{% endblock %}` in your template file.

## HTML basics

Use standard HTML tags to build your content:

```html
{% block content %}
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>

    <p>A paragraph of text. You can make words <strong>bold</strong> or <em>italic</em>.</p>

    <a href="https://example.com">A link</a>

    <img src="https://placehold.co/400x200" alt="Description of image">

    <ul>
        <li>Bullet point one</li>
        <li>Bullet point two</li>
    </ul>

    <ol>
        <li>Numbered item one</li>
        <li>Numbered item two</li>
    </ol>
{% endblock %}
```

## Using variables from Python

You can pass data from Python to your template. In `__init__.py`:

```python
@app.route("/greeting")
def greeting():
    return render_template("greeting.html", name="Ria", age=14)
```

Then in `greeting.html`:

```html
{% block content %}
    <h1>Hello, {{ name }}!</h1>
    <p>You are {{ age }} years old.</p>
{% endblock %}
```

`{{ ... }}` prints a Python value into the page.

## Lists from Python

Pass a list and loop over it with `{% for %}`:

```python
@app.route("/hobbies")
def hobbies():
    hobby_list = ["Reading", "Coding", "Drawing"]
    return render_template("hobbies.html", hobbies=hobby_list)
```

```html
{% block content %}
    <h1>My Hobbies</h1>
    <ul>
        {% for hobby in hobbies %}
            <li>{{ hobby }}</li>
        {% endfor %}
    </ul>
{% endblock %}
```

## Showing content conditionally

Use `{% if %}` to show or hide content:

```html
{% block content %}
    <h1>Welcome, {{ name }}</h1>

    {% if age >= 18 %}
        <p>You are an adult.</p>
    {% else %}
        <p>You are under 18.</p>
    {% endif %}
{% endblock %}
```

## Adding a table

```html
<table>
    <tr>
        <th>Subject</th>
        <th>Grade</th>
    </tr>
    <tr>
        <td>Maths</td>
        <td>A</td>
    </tr>
    <tr>
        <td>English</td>
        <td>B</td>
    </tr>
</table>
```

## Quick reference

| What you want         | HTML / Jinja               |
|-----------------------|----------------------------|
| Heading               | `<h1>` to `<h6>`          |
| Paragraph             | `<p>...</p>`               |
| Bold text             | `<strong>...</strong>`     |
| Italic text           | `<em>...</em>`             |
| Link                  | `<a href="url">text</a>`  |
| Image                 | `<img src="url" alt="..">` |
| Bullet list           | `<ul><li>...</li></ul>`    |
| Numbered list         | `<ol><li>...</li></ol>`    |
| Print a variable      | `{{ variable }}`           |
| Loop                  | `{% for x in list %}`      |
| Condition             | `{% if condition %}`       |
