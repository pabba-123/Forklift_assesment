import cv2
import xml.etree.ElementTree as ET
import numpy as np

# ==========================
# CONFIG
# ==========================

VIDEO_PATH = "input_video.mp4"
XML_PATH = "annotations.xml"
OUTPUT_PATH = "output_video.mp4"

# BGR Colors
COLORS = {
    "forklift":       (255, 0, 0),      # Blue
    "forklift_pole":  (0, 255, 255),    # Yellow
    "forklift_teeth": (0, 0, 255),      # Red
    "pallet":         (0, 255, 0),      # Green
}

LABELS = {
    "forklift":       "FORKLIFT",
    "forklift_pole":  "FORKLIFT POLE",
    "forklift_teeth": "TEETH",
    "pallet":         "PALLET",
}


# ==========================
# XML PARSER
# ==========================

def parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    frame_data = {}

    for track in root.findall("track"):
        track_id = track.attrib.get("id", "0")
        label = track.attrib.get("label", "")

        for polygon in track.findall("polygon"):
            frame_no = int(polygon.attrib["frame"])
            points_str = polygon.attrib["points"]

            points = []
            for point in points_str.split(";"):
                x, y = point.split(",")
                points.append([int(float(x)), int(float(y))])

            if frame_no not in frame_data:
                frame_data[frame_no] = []

            frame_data[frame_no].append({
                "track_id": track_id,
                "label": label,
                "points": np.array(points, dtype=np.int32)
            })

    return frame_data


# ==========================
# COMPUTE DYNAMIC THRESHOLDS
# Scan all frames to find actual min/max Y of teeth/pallet
# ==========================

def compute_dynamic_thresholds(frame_data):
    y_values = []

    for frame_no, objects in frame_data.items():
        for obj in objects:
            label = obj["label"]
            pts = obj["points"]

            if label == "forklift_teeth":
                y_values.append(np.max(pts[:, 1]))
            elif label == "pallet":
                # Only use pallet if no teeth in this frame
                has_teeth = any(o["label"] == "forklift_teeth" for o in objects)
                if not has_teeth:
                    y_values.append(np.max(pts[:, 1]))

    if not y_values:
        print("[WARN] No teeth/pallet Y values found. Using fallback thresholds.")
        return None

    y_min = min(y_values)
    y_max = max(y_values)
    y_range = y_max - y_min

    # Divide the actual movement range into 4 equal buckets
    t1 = y_min + y_range * 0.25   # D -> C boundary
    t2 = y_min + y_range * 0.50   # C -> B boundary
    t3 = y_min + y_range * 0.75   # B -> A boundary

    print(f"[INFO] Teeth/Pallet Y range: min={y_min:.0f}, max={y_max:.0f}")
    print(f"[INFO] Thresholds -> D<{t1:.0f} | C<{t2:.0f} | B<{t3:.0f} | A")

    return t1, t2, t3


def get_row(y, thresholds, frame_height):
    if thresholds is None:
        # Fallback to frame-based quarters
        q1 = frame_height * 0.25
        q2 = frame_height * 0.50
        q3 = frame_height * 0.75
        if y > q3:
            return "A"
        elif y > q2:
            return "B"
        elif y > q1:
            return "C"
        else:
            return "D"

    t1, t2, t3 = thresholds
    if y > t3:
        return "A"
    elif y > t2:
        return "B"
    elif y > t1:
        return "C"
    else:
        return "D"


# ==========================
# DRAW LABEL
# ==========================

def draw_label(frame, text, x, y, color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 2

    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    label_y = max(y - 5, text_h + 5)

    # Dark background
    cv2.rectangle(
        frame,
        (x, label_y - text_h - baseline - 2),
        (x + text_w + 6, label_y + baseline + 2),
        (20, 20, 20),
        -1
    )

    # Colored border
    cv2.rectangle(
        frame,
        (x, label_y - text_h - baseline - 2),
        (x + text_w + 6, label_y + baseline + 2),
        color,
        1
    )

    # White text
    cv2.putText(
        frame,
        text,
        (x + 3, label_y - baseline),
        font,
        font_scale,
        (255, 255, 255),
        thickness
    )


# ==========================
# MAIN
# ==========================

def main():

    annotations = parse_xml(XML_PATH)

    # Pre-scan: compute dynamic thresholds from actual Y movement
    thresholds = compute_dynamic_thresholds(annotations)

    cap = cv2.VideoCapture(VIDEO_PATH)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    frame_no = 0
    prev_row = "A"  # Carry forward last known row

    print("\n[INFO] Processing frames...\n")

    while True:

        ret, frame = cap.read()
        if not ret:
            break

        row = prev_row  # Carry forward instead of always defaulting to A
        forklift_id = "1"
        teeth_y_log = None

        if frame_no in annotations:

            objects = annotations[frame_no]

            # Check if teeth exist in this frame
            has_teeth = any(o["label"] == "forklift_teeth" for o in objects)

            # Pass 1: transparent overlays
            for obj in objects:
                label = obj["label"]
                pts   = obj["points"]
                color = COLORS.get(label, (255, 255, 255))

                overlay = frame.copy()
                cv2.fillPoly(overlay, [pts], color)
                frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

            # Pass 2: borders, boxes, labels
            for obj in objects:
                label         = obj["label"]
                pts           = obj["points"]
                color         = COLORS.get(label, (255, 255, 255))
                display_label = LABELS.get(label, label.upper())

                cv2.polylines(frame, [pts], True, color, 2)

                x, y_box, w, h = cv2.boundingRect(pts)
                cv2.rectangle(frame, (x, y_box), (x + w, y_box + h), color, 2)

                draw_label(frame, display_label, x, y_box, color)

                if label == "forklift":
                    forklift_id = obj["track_id"]

                # Priority: use teeth first
                if label == "forklift_teeth":
                    teeth_y = np.max(pts[:, 1])
                    teeth_y_log = teeth_y
                    row = get_row(teeth_y, thresholds, height)

                # Only use pallet if NO teeth in this frame
                elif label == "pallet" and not has_teeth:
                    pallet_y = np.max(pts[:, 1])
                    teeth_y_log = pallet_y
                    row = get_row(pallet_y, thresholds, height)

        # Log every 30 frames for debugging
        if frame_no % 30 == 0:
            src = "teeth" if teeth_y_log else "carried-forward"
            print(f"  Frame {frame_no:4d} | Y={str(round(teeth_y_log)) if teeth_y_log else 'N/A':>6} | Row={row} ({src})")

        prev_row = row

        # Status box (top-left)
        status_text = f"FORKLIFT {forklift_id} TEETH HEIGHT : 5-{row}"

        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.75
        thickness  = 2

        (tw, th), baseline = cv2.getTextSize(status_text, font, font_scale, thickness)

        box_x1, box_y1 = 10, 10
        box_x2 = box_x1 + tw + 20
        box_y2 = box_y1 + th + 20

        overlay = frame.copy()
        cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.65, frame, 0.35, 0)

        CYAN_BGR = (255, 255, 0)

        cv2.putText(
            frame,
            status_text,
            (box_x1 + 10, box_y1 + th + 5),
            font,
            font_scale,
            CYAN_BGR,
            thickness
        )

        out.write(frame)
        frame_no += 1

    cap.release()
    out.release()

    print(f"\n[DONE] Output saved as: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()