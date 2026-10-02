"""Infer nearby translated joints from complete world-space Part shapes.

The input shapes already carry world placement. No input is changed and no
rotation is proposed. Projection and a finite world radius both limit capture.
"""
import math
import FreeCAD as App
import Part

_EPS = 1e-6
_AXIS = {'X': 'x', 'Y': 'y', 'Z': 'z'}
_PRIORITY = {'extension': 0, 'flush': 1, 'face': 2, 'corner': 3}


def _near_boxes(left, right, padding=0):
    return all(getattr(left, c+'Max') + padding >= getattr(right, c+'Min') and
               getattr(right, c+'Max') + padding >= getattr(left, c+'Min')
               for c in ('X', 'Y', 'Z'))


def _faces(shape):
    result = []
    for index, face in enumerate(shape.Faces):
        if isinstance(face.Surface, Part.Plane):
            u0, u1, v0, v1 = face.ParameterRange
            normal = face.normalAt((u0+u1)/2, (v0+v1)/2)
            result.append((index, face, face.CenterOfMass, normal,
                           [v.Point for v in face.Vertexes]))
    return result


def connection_snap(source_shape, target_shapes, raw_delta, project,
                    tolerance_px=18, world_tolerance=50, axis=None, previous=None):
    """Return delta/contact points/label/kind/key for a nearby safe joint.

    ``target_shapes`` contains (label, world_shape) pairs. ``project`` maps a
    world vector to two pixel coordinates. ``source`` is before translation;
    ``target`` is its proposed destination. ``previous`` provides small capture
    hysteresis only for the same geometric connection, within the world limit.
    """
    if axis is not None and axis not in _AXIS:
        raise ValueError('Unknown movement axis: {}'.format(axis))
    if tolerance_px <= 0 or world_tolerance <= 0 or source_shape.isNull():
        return None
    raw = App.Vector(raw_delta)
    moved_raw = source_shape.copy()
    moved_raw.translate(raw)
    targets = [(index, label, shape) for index, (label, shape) in enumerate(target_shapes)
               if not shape.isNull() and
               _near_boxes(moved_raw.BoundBox, shape.BoundBox, world_tolerance)]
    if not targets:
        return None
    source_faces = _faces(source_shape)
    source_min = min((f[1].Area for f in source_faces), default=0)
    candidates = {}

    def propose(point, destination, kind, identity, label, faces=None):
        correction = destination - point - raw
        distance = correction.Length
        if distance > world_tolerance + _EPS:
            return
        if axis is not None and any(abs(getattr(correction, c)) > _EPS
                                    for c in 'xyz' if c != _AXIS[axis]):
            return
        start_px = project(point + raw)
        end_px = project(destination)
        pixels = math.hypot(start_px[0]-end_px[0], start_px[1]-end_px[1])
        retained = previous is not None and previous.get('key') == identity
        radius = tolerance_px + (2 if retained else 0)
        if not math.isfinite(pixels) or pixels > radius:
            return
        delta = destination - point
        delta_key = (tuple(round(getattr(delta, c), 6) for c in 'xyz'),
                     bool(faces is not None and faces[2]))
        # Across different joints, prefer smaller full world corrections.
        # The bounded bonus favors a sensible nearby extension or flush fit.
        bonus = {'extension': 8, 'flush': 4, 'face': 0, 'corner': 0}[kind]
        score = (max(0, distance-bonus), _PRIORITY[kind],
                 max(0, pixels-(2 if retained else 0)), distance)
        existing = candidates.get(delta_key)
        if existing is None or score < existing[0]:
            candidates[delta_key] = (score, {'delta': delta, 'source': App.Vector(point),
                'target': App.Vector(destination), 'label': label, 'kind': kind,
                'key': identity}, faces)

    for target_index, label, target in targets:
        target_faces = _faces(target)
        target_min = min((f[1].Area for f in target_faces), default=0)
        for si, sf, sc, sn, sv in source_faces:
            for ti, tf, tc, tn, tv in target_faces:
                if sn.dot(tn) > -1 + _EPS:
                    continue
                separation = (tc-sc-raw).dot(sn)
                if abs(separation) > world_tolerance:
                    continue
                if not _near_boxes(sf.translated(raw).BoundBox, tf.BoundBox, world_tolerance):
                    continue
                face_pair = (sf, tf, False)
                key = (target_index, label, si, ti)
                # Smallest matching faces identify the timber's end profile.
                # Validate equal finite profiles after the proposed translation.
                if (abs(sf.Area-tf.Area) <= _EPS*max(1,sf.Area) and
                    sf.Area <= source_min*(1+_EPS) and
                    tf.Area <= target_min*(1+_EPS)):
                    propose(sc, tc, 'extension', key+('extension',), label,
                            (sf, tf, True))
                destination = sc + raw + sn*separation
                propose(sc, destination, 'face', key+('face',), label, face_pair)
                # Face corners align the rail end with an upright's boundary,
                # while finite face overlap and solid collision guard the joint.
                for svi, sp in enumerate(sv):
                    for tvi, tp in enumerate(tv):
                        propose(sp, tp, 'flush', key+('flush',svi,tvi), label, face_pair)
        for si, vertex in enumerate(source_shape.Vertexes):
            sp = vertex.Point
            for ti, target_vertex in enumerate(target.Vertexes):
                propose(sp, target_vertex.Point, 'corner',
                        (target_index,label,'corner',si,ti), label)

    # Most cursor positions yield no proposals. Sort and deduplicate before any
    # boolean operations, then stop at the first valid connection.
    # Treat full profile and partial contact on the SAME face pair as one
    # inferred joint. Try its extension first, but rank that joint against all
    # OTHER joints using the full correction. If extension validation fails,
    # the remaining contacts re-enter the global ranking without suppression.
    groups = {}
    for candidate in candidates.values():
        _score, result, faces = candidate
        group = result['key'][:4] if faces is not None else result['key']
        groups.setdefault(group, []).append(candidate)
    for group in groups.values():
        group.sort(key=lambda c: (c[1]['kind'] != 'extension', c[0]))
    while groups:
        best_group = min(groups, key=lambda key: groups[key][0][0])
        _score, result, faces = groups[best_group].pop(0)
        if not groups[best_group]:
            del groups[best_group]
        delta = result['delta']
        if faces is not None:
            source_face, target_face, equal_profile = faces
            overlap = source_face.translated(delta).common(target_face)
            area = overlap.Area
            if area <= _EPS:
                continue
            if equal_profile and abs(area-source_face.Area) > _EPS*max(1,source_face.Area):
                continue
            contact = overlap.CenterOfMass
            result['source'] = contact-delta
            result['target'] = contact
        moved = source_shape.copy()
        moved.translate(delta)
        collision = False
        for _index, _label, target in targets:
            if _near_boxes(moved.BoundBox, target.BoundBox):
                if moved.common(target).Volume > _EPS:
                    collision = True
                    break
        if not collision:
            return result
    return None
