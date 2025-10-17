import base64
import json
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO

import matplotlib
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views import View

import matplotlib.pyplot as plt

from .forms import ReservationForm

matplotlib.use('Agg')

INTERVAL_PATTERN = re.compile(r'^(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)$')

def hello_world(request):
    return HttpResponse("Again Hello World")


class HelloEthiopia(View):
    def get(self, request):
        return HttpResponse("Again Hello Ethiopia")
    

def home(request):
    form = ReservationForm()            

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("success")
        
    return render(request, 'index.html', {'form' : form})

def statistics_view(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

        data_type = payload.get('dataType')
        rows = payload.get('rows') or []
        using_cumulative = bool(payload.get('usingCumulative'))

        try:
            if data_type == 'ungrouped':
                parsed_rows = _parse_ungrouped_rows(rows, using_cumulative)
                stats = _compute_ungrouped_statistics(parsed_rows)
                histogram = _render_ungrouped_histogram(stats['values'], stats['median'], stats['mode_values'])
                ogive = _render_ogive(stats['ogive_points'], stats['total_frequency'], stats['median'], xlabel='Values')
                mode_display = stats['mode_display']
                modal_label = 'Not applicable'
            elif data_type == 'grouped':
                classes = _parse_grouped_rows(rows, using_cumulative)
                stats = _compute_grouped_statistics(classes)
                histogram = _render_grouped_histogram(classes, stats['median'], stats['mode'], stats['modal_index'])
                ogive = _render_ogive(stats['cumulative_points'], stats['total_frequency'], stats['median'], xlabel='Upper class boundary')
                mode_display = stats['mode_display']
                modal_label = stats['modal_label']
            else:
                raise ValueError('Select either ungrouped or grouped data.')
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        response = {
            'type': 'Ungrouped data' if data_type == 'ungrouped' else 'Grouped data',
            'total_frequency': stats['total_frequency'],
            'mean': _format_number(stats['mean']),
            'median': _format_number(stats['median']),
            'mode': mode_display,
            'modal_label': modal_label,
            'histogram_image': histogram,
            'ogive_image': ogive,
        }
        return JsonResponse(response)

    return render(request, 'statistics.html')

def _parse_decimal(value, label):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f'"{value}" is not a valid number for {label}.')

def _parse_frequency(value, label, default=None):
    if value is None or str(value).strip() == '':
        if default is None:
            raise ValueError(f'{label} is required.')
        return default

    freq = _parse_decimal(value, label)
    if freq <= 0:
        raise ValueError(f'{label} must be greater than zero.')
    if freq != freq.to_integral_value():
        raise ValueError(f'{label} must be a whole number.')
    return int(freq)

def _parse_ungrouped_rows(rows, using_cumulative=False):
    entries = []
    for index, row in enumerate(rows, start=1):
        value_text = (row or {}).get('value', '').strip()
        if not value_text:
            continue

        value = _parse_decimal(value_text, f'value (row {index})')
        entry = {'value': float(value), 'index': index}

        if using_cumulative:
            cumulative_text = (row or {}).get('cumulative', '')
            cumulative = _parse_frequency(cumulative_text, f'cumulative frequency (row {index})')
            entry['cumulative'] = cumulative
        else:
            frequency_text = (row or {}).get('frequency', '')
            frequency = _parse_frequency(frequency_text, f'frequency (row {index})', default=1)
            entry['frequency'] = frequency

        entries.append(entry)

    if not entries:
        raise ValueError('Enter at least one value with a valid frequency.')

    if using_cumulative:
        processed = []
        previous_cumulative = 0
        for entry in sorted(entries, key=lambda item: (item['value'], item['index'])):
            cumulative = entry['cumulative']
            if cumulative <= previous_cumulative:
                raise ValueError('Cumulative frequencies must strictly increase when using cumulative input.')
            frequency = cumulative - previous_cumulative
            processed.append((entry['value'], frequency))
            previous_cumulative = cumulative
        total_frequency = previous_cumulative
    else:
        processed = [(entry['value'], entry['frequency']) for entry in entries]
        total_frequency = sum(freq for _, freq in processed)

    if total_frequency <= 0:
        raise ValueError('Total frequency must be greater than zero.')

    return processed

def _parse_interval(interval_text, index):
    cleaned = interval_text.strip().lower().replace(' to ', '-')
    match = INTERVAL_PATTERN.match(cleaned)
    if not match:
        raise ValueError(f'"{interval_text}" is not a valid interval on row {index}. Use formats like 50-60.')
    lower = _parse_decimal(match.group(1), f'interval lower bound (row {index})')
    upper = _parse_decimal(match.group(2), f'interval upper bound (row {index})')
    if lower >= upper:
        raise ValueError(f'Lower bound must be less than upper bound on row {index}.')
    return float(lower), float(upper)

def _parse_grouped_rows(rows, using_cumulative):
    classes = []
    previous_upper = None
    previous_cumulative = 0

    for index, row in enumerate(rows, start=1):
        interval_text = (row or {}).get('interval', '').strip()
        if not interval_text:
            continue

        lower, upper = _parse_interval(interval_text, index)
        if previous_upper is not None and lower < previous_upper:
            raise ValueError('Class intervals must be in ascending order and not overlap.')

        if using_cumulative:
            cumulative_value = _parse_frequency((row or {}).get('cumulative', ''), f'cumulative frequency (row {index})')
            if cumulative_value <= previous_cumulative:
                raise ValueError('Cumulative frequencies must strictly increase.')
            frequency = cumulative_value - previous_cumulative
            previous_cumulative = cumulative_value
        else:
            frequency = _parse_frequency((row or {}).get('frequency', ''), f'frequency (row {index})')
            previous_cumulative += frequency

        classes.append({'lower': lower, 'upper': upper, 'frequency': frequency})
        previous_upper = upper

    if not classes:
        raise ValueError('Enter at least one class interval with a valid frequency.')

    total_frequency = sum(cls['frequency'] for cls in classes)
    if total_frequency <= 0:
        raise ValueError('Total frequency must be greater than zero.')

    return classes

def _compute_ungrouped_statistics(pairs):
    values = []
    for value, frequency in sorted(pairs, key=lambda item: item[0]):
        values.extend([value] * frequency)

    total_frequency = len(values)
    mean_value = sum(values) / total_frequency if total_frequency else None

    if total_frequency == 0:
        median_value = None
    elif total_frequency % 2 == 1:
        median_value = values[total_frequency // 2]
    else:
        median_value = (values[total_frequency // 2 - 1] + values[total_frequency // 2]) / 2

    frequencies = {}
    for value, freq in pairs:
        frequencies.setdefault(value, 0)
        frequencies[value] += freq

    sorted_items = sorted(frequencies.items())
    max_frequency = max((freq for _, freq in sorted_items), default=0)
    mode_values = [val for val, freq in sorted_items if freq == max_frequency] if max_frequency else []
    mode_display = ', '.join(str(_format_number(val)) for val in mode_values) if mode_values else '—'

    ogive_points = []
    running_total = 0
    if sorted_items:
        first_value = sorted_items[0][0]
        ogive_points.append((first_value, 0))
        for value, freq in sorted_items:
            running_total += freq
            ogive_points.append((value, running_total))

    return {
        'total_frequency': total_frequency,
        'mean': mean_value,
        'median': median_value,
        'mode_display': mode_display,
        'mode_values': mode_values,
        'values': values,
        'ogive_points': ogive_points,
    }

def _compute_grouped_statistics(classes):
    total_frequency = sum(cls['frequency'] for cls in classes)
    if total_frequency <= 0:
        raise ValueError('Total frequency must be greater than zero.')

    mean_value = sum(((cls['lower'] + cls['upper']) / 2) * cls['frequency'] for cls in classes) / total_frequency

    cumulative = 0
    cumulative_before = 0
    median_value = None
    median_class = None
    cumulative_points = []
    if classes:
        cumulative_points.append((classes[0]['lower'], 0))

    for cls in classes:
        cumulative += cls['frequency']
        cumulative_points.append((cls['upper'], cumulative))
        if median_class is None and cumulative >= total_frequency / 2:
            median_class = cls
            cumulative_before = cumulative - cls['frequency']

    if median_class:
        h = median_class['upper'] - median_class['lower']
        if h > 0 and median_class['frequency'] > 0:
            median_value = median_class['lower'] + ((total_frequency / 2 - cumulative_before) / median_class['frequency']) * h

    max_freq = max(classes, key=lambda cls: cls['frequency'])['frequency']
    mode_candidates = [idx for idx, cls in enumerate(classes) if cls['frequency'] == max_freq]
    modal_index = mode_candidates[0]
    modal_class = classes[modal_index]
    modal_label = f"{_format_number(modal_class['lower'])} – {_format_number(modal_class['upper'])}"

    prev_freq = classes[modal_index - 1]['frequency'] if modal_index > 0 else 0
    next_freq = classes[modal_index + 1]['frequency'] if modal_index < len(classes) - 1 else 0
    h = modal_class['upper'] - modal_class['lower']
    denominator = (modal_class['frequency'] - prev_freq) + (modal_class['frequency'] - next_freq)
    if h > 0 and denominator != 0:
        mode_value = modal_class['lower'] + ((modal_class['frequency'] - prev_freq) / denominator) * h
    else:
        mode_value = (modal_class['lower'] + modal_class['upper']) / 2

    mode_display = str(_format_number(mode_value)) if mode_value is not None else '—'

    return {
        'total_frequency': total_frequency,
        'mean': mean_value,
        'median': median_value,
        'mode': mode_value,
        'mode_display': mode_display,
        'modal_label': modal_label,
        'cumulative_points': cumulative_points,
        'modal_index': modal_index,
    }

def _render_ungrouped_histogram(values, median_value, mode_values):
    if not values:
        return None

    bins = min(10, max(1, len(set(values))))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=bins, color='#6366f1', edgecolor='#312e81', alpha=0.85)
    ax.set_xlabel('Values')
    ax.set_ylabel('Frequency')
    if median_value is not None:
        ax.axvline(median_value, color='#0ea5e9', linestyle='--', linewidth=1.4,
                   label=f'Median {_format_number(median_value)}')
    for index, mode_value in enumerate(mode_values):
        ax.axvline(mode_value, color='#f97316', linestyle='-', linewidth=1.2,
                   label='Mode' if index == 0 else None)
    ax.grid(alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend()
    fig.tight_layout()
    return _figure_to_base64(fig)

def _render_grouped_histogram(classes, median_value, mode_value, modal_index):
    fig, ax = plt.subplots(figsize=(7, 4))
    for cls in classes:
        width = cls['upper'] - cls['lower']
        ax.bar(cls['lower'], cls['frequency'], width=width, align='edge', color='#38bdf8', edgecolor='#0f172a', alpha=0.85)

    if median_value is not None:
        ax.axvline(median_value, color='#0ea5e9', linestyle='--', linewidth=1.4,
                   label=f'Median {_format_number(median_value)}')

    if 0 <= modal_index < len(classes):
        modal_class = classes[modal_index]
        prev_class = classes[modal_index - 1] if modal_index > 0 else None
        next_class = classes[modal_index + 1] if modal_index < len(classes) - 1 else None

        if prev_class and next_class:
            ax.plot([prev_class['upper'], modal_class['lower']],
                    [prev_class['frequency'], modal_class['frequency']],
                    color='#f97316', linestyle='--', linewidth=1.2,
                    label='Mode construction')
            ax.plot([modal_class['upper'], next_class['lower']],
                    [modal_class['frequency'], next_class['frequency']],
                    color='#f97316', linestyle='--', linewidth=1.2)

            intersection = _line_intersection(
                (prev_class['upper'], prev_class['frequency']),
                (modal_class['lower'], modal_class['frequency']),
                (next_class['lower'], next_class['frequency']),
                (modal_class['upper'], modal_class['frequency'])
            )
            if intersection:
                mode_x, mode_y = intersection
                ax.scatter(mode_x, mode_y, color='#f97316')
                ax.vlines(mode_x, 0, mode_y, color='#f97316', linewidth=1.4, label='Mode')
        elif mode_value is not None:
            ax.vlines(mode_value, 0, modal_class['frequency'], color='#f97316', linewidth=1.4, label='Mode')
    ax.set_xlabel('Class intervals')
    ax.set_ylabel('Frequency')
    ax.grid(alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend()
    fig.tight_layout()
    return _figure_to_base64(fig)

def _render_ogive(points, total_frequency, median_value, xlabel):
    fig, ax = plt.subplots(figsize=(7, 4))
    median_level = total_frequency / 2 if total_frequency else None
    intersection_x = None
    if points:
        xs, ys = zip(*points)
        ax.plot(xs, ys, marker='o', color='#22c55e')
        if median_level is not None:
            for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
                if (y0 <= median_level <= y1) or (y1 <= median_level <= y0):
                    if y1 == y0:
                        intersection_x = x1
                    else:
                        ratio = (median_level - y0) / (y1 - y0)
                        intersection_x = x0 + ratio * (x1 - x0)
                    break
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Cumulative frequency')
    if median_level is not None and points:
        start_x = points[0][0]
        target_x = intersection_x if intersection_x is not None else median_value
        if target_x is not None:
            ax.hlines(median_level, start_x, target_x, colors='#0ea5e9', linestyles='--', linewidth=1.2,
                      label='Median level (N/2)')
            ax.vlines(target_x, 0, median_level, colors='#0ea5e9', linestyles='-', linewidth=1.5,
                      label=f'Median {_format_number(target_x)}')
            ax.scatter(target_x, median_level, color='#0ea5e9')
    ax.grid(alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend()
    fig.tight_layout()
    return _figure_to_base64(fig)

def _figure_to_base64(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('ascii')

def _line_intersection(p1, p2, p3, p4):
    (x1, y1), (x2, y2) = p1, p2
    (x3, y3), (x4, y4) = p3, p4
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1e-12:
        return None
    numerator_x = (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    numerator_y = (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    return numerator_x / denominator, numerator_y / denominator

def _format_number(value):
    if value is None:
        return None
    rounded = round(float(value), 4)
    return int(rounded) if rounded.is_integer() else rounded