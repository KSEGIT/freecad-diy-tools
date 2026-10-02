"""Infer nearby translated joints from complete world-space Part shapes.

The input shapes already carry world placement. No input is changed and no
rotation is proposed. Projection and a finite world radius limit normal capture.
Explicitly visible target faces can resolve depth along their feature camera ray.
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
                    tolerance_px=18, world_tolerance=50, axis=None, previous=None,
                    view_direction=None, depth_faces=None, excluded_keys=None, intent=None):
    """Return delta/contact points/label/kind/key for a nearby safe joint.

    ``target_shapes`` contains (label, world_shape) pairs. ``project`` maps a
    world vector to two pixel coordinates. ``source`` is before translation;
    ``target`` is its proposed destination. ``previous`` widens release by eight
    pixels and favors the same connection, within the world limit.
    ``depth_faces`` maps ORIGINAL target-list indices to visible zero-based
    target face indices. These faces may resolve camera depth beyond the world
    radius, but lateral correction and screen capture remain limited.
    ``view_direction`` is a vector or callable(world_point) returning its camera
    ray direction. No depth inference occurs unless both arguments are supplied.
    ``intent`` optionally restricts proposals to target_index and its visible
    component (FaceN, EdgeN or VertexN). point and source_pickup rank nearby
    connection features. All targets remain collision blockers.
    ``excluded_keys`` skips individual rejected connections, preserving all
    target solids as collision blockers and other contacts on those solids.
    """
    if axis is not None and axis not in _AXIS:
        raise ValueError('Unknown movement axis: {}'.format(axis))
    if tolerance_px <= 0 or world_tolerance <= 0 or source_shape.isNull():
        return None
    intent = intent or {}
    intended_index = intent.get('target_index')
    aim = intent.get('point')
    pickup = intent.get('source_pickup')
    depth_faces = depth_faces or {}
    excluded_keys = excluded_keys or set()
    def ray_direction(point):
        value = view_direction(point) if callable(view_direction) else view_direction
        if value is None:
            return None
        direction = App.Vector(value)
        if direction.Length <= _EPS:
            return None
        direction.normalize()
        return direction
    raw = App.Vector(raw_delta)
    moved_raw = source_shape.copy()
    moved_raw.translate(raw)
    targets = [(index, label, shape) for index, (label, shape) in enumerate(target_shapes)
               if not shape.isNull() and
               (_near_boxes(moved_raw.BoundBox, shape.BoundBox, world_tolerance)
                or (index in depth_faces and view_direction is not None))]
    if not targets:
        return None
    source_faces = _faces(source_shape)
    source_min = min((f[1].Area for f in source_faces), default=0)
    candidates = {}

    def propose(point, destination, kind, identity, label, faces=None, depth=False, adjacent_planes=0):
        if identity in excluded_keys:
            return
        correction = destination - point - raw
        distance = correction.Length
        lateral = distance
        if depth:
            direction = ray_direction(point + raw)
            if direction is None:
                return
            lateral = (correction-direction*correction.dot(direction)).Length
        if lateral > world_tolerance + _EPS:
            return
        if axis is not None and any(abs(getattr(correction, c)) > _EPS
                                    for c in 'xyz' if c != _AXIS[axis]):
            return
        start_px = project(point + raw)
        end_px = project(destination)
        pixels = math.hypot(start_px[0]-end_px[0], start_px[1]-end_px[1])
        retained = previous is not None and previous.get('key') == identity
        radius = max(tolerance_px+8,26) if retained else tolerance_px
        if not math.isfinite(pixels) or pixels > radius:
            return
        delta = destination - point
        delta_key = (tuple(round(getattr(delta, c), 6) for c in 'xyz'),
                     bool(faces is not None and faces[2]))
        # Across different joints, prefer smaller full world corrections.
        # The bounded bonus favors a sensible nearby extension or flush fit.
        bonus = {'extension': 8, 'flush': 4, 'face': 0, 'corner': 0}[kind]
        score = ((0, max(0, pixels-(2 if retained else 0)-(4 if kind == "flush" else 0)), max(0,lateral-bonus),
                  _PRIORITY[kind], distance) if depth else
                 (1, max(0, distance-bonus), _PRIORITY[kind],
                  max(0, pixels-(2 if retained else 0)), distance))
        # Cursor intent ranks connection features near the held point and the
        # visible destination feature. Keep correction as the primary limit;
        # this affinity only resolves competing nearby connections.
        if aim is not None and pickup is not None:
            pp = project(pickup)
            sp = project(point)
            ap = project(aim)
            dp = project(destination)
            affinity = math.hypot(pp[0]-sp[0],pp[1]-sp[1]) + math.hypot(ap[0]-dp[0],ap[1]-dp[1])
            score = (score[0],score[1]+min(affinity*.12,30)) + score[2:]
        if retained:
            score = (score[0],max(0,score[1]-8)) + score[2:]
        existing = candidates.get(delta_key)
        rank = (kind != 'extension',-adjacent_planes,score)
        existing_rank = None if existing is None else (
            existing[1]['kind'] != 'extension',-existing[1].get('adjacent_planes',0),existing[0])
        if existing_rank is None or rank < existing_rank:
            candidates[delta_key] = (score, {'delta': delta, 'source': App.Vector(point),
                'target': App.Vector(destination), 'label': label, 'kind': kind,
                'key': identity, 'depth': depth,
                'target_face_index': identity[3] if depth else None, 'pixels': pixels,
                'adjacent_planes': adjacent_planes}, faces)

    def incident_directions(face, point):
        directions = []
        for edge in face.Edges:
            if not isinstance(edge.Curve, Part.Line) or len(edge.Vertexes) != 2:
                continue
            a,b = (vertex.Point for vertex in edge.Vertexes)
            if min((a-point).Length,(b-point).Length) > _EPS:
                continue
            direction = b-a
            if direction.Length > _EPS:
                direction.normalize()
                directions.append(direction)
        return directions

    def adjacent_flushes(source_face, target_face, base_delta, key, label, depth):
        # One aligned edge leaves its along-edge offset unchanged. At a nearby
        # boundary, two independent parallel edge pairs also align the adjacent
        # planes. Capture only a small in-plane correction; mid-rail placement
        # must still slide freely, and a distant endpoint must not attract it.
        if intended_index is None:
            return
        center = source_face.CenterOfMass
        for svi, vertex in enumerate(source_face.Vertexes):
            sp = vertex.Point
            source_directions = incident_directions(source_face,sp)
            for tvi, target_vertex in enumerate(target_face.Vertexes):
                tp = target_vertex.Point
                if component.startswith('Edge') and feature is not None and not any(v.isSame(target_vertex) for v in feature.Vertexes):
                    continue
                if component.startswith('Vertex') and feature is not None and not target_vertex.isSame(feature):
                    continue
                identity = key+('depth_adjacent' if depth else 'adjacent',svi,tvi)
                retained = previous is not None and previous.get('key') == identity
                delta = tp-sp
                in_plane = delta-base_delta
                if in_plane.Length > min(world_tolerance,12)+(8 if retained else 0):
                    continue
                a = project(center+base_delta)
                b = project(center+delta)
                if math.hypot(a[0]-b[0],a[1]-b[1]) > tolerance_px+(8 if retained else 0):
                    continue
                target_directions = incident_directions(target_face,tp)
                matched = [direction for direction in source_directions
                           if any(abs(direction.dot(other)) > 1-_EPS for other in target_directions)]
                if not any(abs(a.dot(b)) < 1-_EPS for a in matched for b in matched):
                    continue
                propose(center,center+delta,'flush',identity,label,
                        (source_face,target_face,False),depth,adjacent_planes=2)

    def edge_flushes(source_face, target_face, base_delta, key, label, depth):
        adjacent_flushes(source_face,target_face,base_delta,key,label,depth)
        # Align parallel finite face edges without pulling a mid-rail joint to
        # an endpoint. Start at the face-contact depth, then preserve distance
        # along the destination edge's supporting line.
        for sei, source_edge in enumerate(source_face.Edges):
            if not isinstance(source_edge.Curve, Part.Line) or len(source_edge.Vertexes) != 2:
                continue
            sa, sb = (vertex.Point for vertex in source_edge.Vertexes)
            source_direction = sb-sa
            if source_direction.Length <= _EPS:
                continue
            source_direction.normalize()
            if pickup is None:
                midpoint = (sa+sb)*.5
            else:
                along_pickup = max(0,min((sb-sa).Length,(pickup-sa).dot(source_direction)))
                midpoint = sa+source_direction*along_pickup
            for tei, target_edge in enumerate(target_face.Edges):
                if component.startswith('Edge') and feature is not None and not target_edge.isSame(feature):
                    continue
                if component.startswith('Vertex') and feature is not None and not any(v.isSame(feature) for v in target_edge.Vertexes):
                    continue
                if not isinstance(target_edge.Curve, Part.Line) or len(target_edge.Vertexes) != 2:
                    continue
                ta, tb = (vertex.Point for vertex in target_edge.Vertexes)
                direction = tb-ta
                length = direction.Length
                if length <= _EPS:
                    continue
                direction.normalize()
                if abs(source_direction.dot(direction)) < 1-_EPS:
                    continue
                along = (midpoint+base_delta-ta).dot(direction)
                if along < -_EPS or along > length+_EPS:
                    continue
                destination = ta+direction*along
                propose(midpoint, destination, 'flush', key+('depth_edge' if depth else 'edge',sei,tei),
                        label, (source_face,target_face,False), depth)

    for target_index, label, target in targets:
        if intended_index is not None and target_index != intended_index:
            continue
        target_faces = _faces(target)
        target_min = min((f[1].Area for f in target_faces), default=0)
        component = intent.get('component','') if target_index == intended_index else ''
        feature = None
        try:
            if component.startswith('Face'):
                feature = target.Faces[int(component[4:])-1]
            elif component.startswith('Edge'):
                feature = target.Edges[int(component[4:])-1]
            elif component.startswith('Vertex'):
                feature = target.Vertexes[int(component[6:])-1]
        except (ValueError,IndexError):
            feature = None
        if feature is not None:
            target_faces = [item for item in target_faces
                            if item[1].isSame(feature) or
                            any(edge.isSame(feature) for edge in item[1].Edges) or
                            any(vertex.isSame(feature) for vertex in item[1].Vertexes)]
        for si, sf, sc, sn, sv in source_faces:
            for ti, tf, tc, tn, tv in target_faces:
                if sn.dot(tn) > -1 + _EPS:
                    continue
                separation = (tc-sc-raw).dot(sn)
                visible_depth = ti in depth_faces.get(target_index, set()) and view_direction is not None
                face_pair = (sf, tf, False)
                key = (target_index, label, si, ti)
                if visible_depth:
                    direction = ray_direction(sc + raw)
                    denominator = 0 if direction is None else direction.dot(sn)
                    if abs(denominator) > _EPS:
                        destination = sc + raw + direction*(separation/denominator)
                        propose(sc, destination, 'face', key+('depth_face',), label, face_pair, True)
                        edge_flushes(sf,tf,destination-sc,key,label,True)
                    if (abs(sf.Area-tf.Area) <= _EPS*max(1,sf.Area) and
                        sf.Area <= source_min*(1+_EPS) and tf.Area <= target_min*(1+_EPS)):
                        propose(sc, tc, 'extension', key+('depth_extension',), label,
                                (sf,tf,True), True)
                    for svi, sp in enumerate(sv):
                        for tvi, tp in enumerate(tv):
                            if feature is not None and component.startswith('Vertex') and (tp-feature.Point).Length > _EPS:
                                continue
                            propose(sp, tp, 'flush', key+('depth_flush',svi,tvi), label,face_pair,True)
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
                if intended_index is not None:
                    edge_flushes(sf,tf,destination-sc,key,label,False)
                # Face corners align the rail end with an upright's boundary,
                # while finite face overlap and solid collision guard the joint.
                for svi, sp in enumerate(sv):
                    for tvi, tp in enumerate(tv):
                        if feature is not None and component.startswith('Vertex') and (tp-feature.Point).Length > _EPS:
                            continue
                        propose(sp, tp, 'flush', key+('flush',svi,tvi), label, face_pair)
        if feature is not None:
            # Explicit planar intent must stay a finite face connection; a
            # coincident lone vertex has no bearing area for a timber joint.
            continue
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
    # Within that same face pair, a bounded two-plane boundary fit takes
    # precedence over partial face/one-edge fits that leave a small offset.
    groups = {}
    for candidate in candidates.values():
        _score, result, faces = candidate
        group = (result.get('depth',False),result['key'][:4]) if faces is not None else result['key']
        groups.setdefault(group, []).append(candidate)
    for group in groups.values():
        group.sort(key=lambda c: (c[1]['kind'] != 'extension',
                                 -c[1].get('adjacent_planes',0),c[0]))
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
        for _label, target in target_shapes:
            if not target.isNull() and _near_boxes(moved.BoundBox, target.BoundBox):
                if moved.common(target).Volume > _EPS:
                    collision = True
                    break
        if not collision:
            return result
    return None
