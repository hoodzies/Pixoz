from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import board
import neopixel
from PIL import Image
import time
import os
import random

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

PIXEL_PIN = board.D21
MATRIX_WIDTH = 16
MATRIX_HEIGHT = 16
NUM_PIXELS = MATRIX_WIDTH * MATRIX_HEIGHT
DEFAULT_BRIGHTNESS = 0.02

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    auto_write=False,
    brightness=DEFAULT_BRIGHTNESS
)

def zigzag_index(x, y):
    if y % 2 == 0:
        return y * MATRIX_WIDTH + x
    else:
        return y * MATRIX_WIDTH + (MATRIX_WIDTH - 1 - x)

def display_frame(image):
    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            r, g, b = image.getpixel((x, y))
            i = zigzag_index(x, y)
            pixels[i] = (r, g, b)
    pixels.show()

def scroll_effect(frames, frame_delay, scroll_delay):
    current = frames[0]
    display_frame(current)
    time.sleep(frame_delay)
    for next_frame in frames[1:]:
        direction = random.choice(['up', 'down', 'left', 'right'])
        for step in range(1, MATRIX_HEIGHT + 1 if direction in ['up', 'down'] else MATRIX_WIDTH + 1):
            scroll_frame = Image.new('RGB', (MATRIX_WIDTH, MATRIX_HEIGHT))
            if direction == 'up':
                scroll_frame.paste(current.crop((0, step, MATRIX_WIDTH, MATRIX_HEIGHT)), (0, 0))
                scroll_frame.paste(next_frame.crop((0, 0, MATRIX_WIDTH, step)), (0, MATRIX_HEIGHT - step))
            elif direction == 'down':
                scroll_frame.paste(current.crop((0, 0, MATRIX_WIDTH, MATRIX_HEIGHT - step)), (0, step))
                scroll_frame.paste(next_frame.crop((0, MATRIX_HEIGHT - step, MATRIX_WIDTH, MATRIX_HEIGHT)), (0, 0))
            elif direction == 'left':
                scroll_frame.paste(current.crop((step, 0, MATRIX_WIDTH, MATRIX_HEIGHT)), (0, 0))
                scroll_frame.paste(next_frame.crop((0, 0, step, MATRIX_HEIGHT)), (MATRIX_WIDTH - step, 0))
            elif direction == 'right':
                scroll_frame.paste(current.crop((0, 0, MATRIX_WIDTH - step, MATRIX_HEIGHT)), (step, 0))
                scroll_frame.paste(next_frame.crop((MATRIX_WIDTH - step, 0, MATRIX_WIDTH, MATRIX_HEIGHT)), (0, 0))
            display_frame(scroll_frame)
            time.sleep(scroll_delay)
        current = next_frame
        display_frame(current)
        time.sleep(frame_delay)

def fade_effect(frames, frame_delay, fade_steps=20):
    current = frames[0]
    display_frame(current)
    time.sleep(frame_delay)
    for next_frame in frames[1:]:
        for alpha in range(1, fade_steps + 1):
            blend = Image.blend(current, next_frame, alpha / fade_steps)
            display_frame(blend)
            time.sleep(frame_delay / fade_steps)
        current = next_frame
        display_frame(current)
        time.sleep(frame_delay)

def simple_effect(frames, frame_delay):
    for frame in frames:
        display_frame(frame)
        time.sleep(frame_delay)

EFFECTS = {
    'simple': simple_effect,
    'scroll': scroll_effect,
    'fade': fade_effect,
}

@app.route('/')
def index():
    return render_template('index.html', filename=None, effect='simple')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    frame_delay = request.form.get('frame_delay', default='0.5')
    try:
        frame_delay = float(frame_delay)
    except ValueError:
        frame_delay = 0.5
    effect = request.form.get('effect', 'simple')
    scroll_delay = 0.05

    if file and file.filename.endswith('.png'):
        filename = 'uploaded.png'
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        img = Image.open(path).convert('RGB')
        width, height = img.size

        if width != MATRIX_WIDTH:
            img = img.resize((MATRIX_WIDTH, height))

        if height % MATRIX_HEIGHT == 0:
            num_frames = height // MATRIX_HEIGHT
            frames = []
            for frame in range(num_frames):
                frame_img = img.crop((0, frame * MATRIX_HEIGHT, MATRIX_WIDTH, (frame + 1) * MATRIX_HEIGHT))
                frame_img = frame_img.transpose(Image.FLIP_LEFT_RIGHT).rotate(180)
                frames.append(frame_img)
        else:
            img = img.resize((MATRIX_WIDTH, MATRIX_HEIGHT))
            img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(180)
            frames = [img]

        # Call the selected effect
        if effect == 'scroll':
            EFFECTS['scroll'](frames, frame_delay, scroll_delay)
        elif effect == 'fade':
            EFFECTS['fade'](frames, frame_delay)
        else:
            EFFECTS['simple'](frames, frame_delay)

        return render_template('index.html', filename=filename, effect=effect)
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/off')
def turn_off():
    pixels.fill((0, 0, 0))
    pixels.show()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
