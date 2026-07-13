// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'db.dart';

// ignore_for_file: type=lint
class $CachedLessonsTable extends CachedLessons
    with TableInfo<$CachedLessonsTable, CachedLesson> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedLessonsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _groupIdMeta = const VerificationMeta(
    'groupId',
  );
  @override
  late final GeneratedColumn<int> groupId = GeneratedColumn<int>(
    'group_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _weekdayMeta = const VerificationMeta(
    'weekday',
  );
  @override
  late final GeneratedColumn<int> weekday = GeneratedColumn<int>(
    'weekday',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pairNumberMeta = const VerificationMeta(
    'pairNumber',
  );
  @override
  late final GeneratedColumn<int> pairNumber = GeneratedColumn<int>(
    'pair_number',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _startsAtMeta = const VerificationMeta(
    'startsAt',
  );
  @override
  late final GeneratedColumn<String> startsAt = GeneratedColumn<String>(
    'starts_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _endsAtMeta = const VerificationMeta('endsAt');
  @override
  late final GeneratedColumn<String> endsAt = GeneratedColumn<String>(
    'ends_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _subjectMeta = const VerificationMeta(
    'subject',
  );
  @override
  late final GeneratedColumn<String> subject = GeneratedColumn<String>(
    'subject',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _roomMeta = const VerificationMeta('room');
  @override
  late final GeneratedColumn<String> room = GeneratedColumn<String>(
    'room',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _weekTypeMeta = const VerificationMeta(
    'weekType',
  );
  @override
  late final GeneratedColumn<String> weekType = GeneratedColumn<String>(
    'week_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _subgroupMeta = const VerificationMeta(
    'subgroup',
  );
  @override
  late final GeneratedColumn<int> subgroup = GeneratedColumn<int>(
    'subgroup',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _teacherNameMeta = const VerificationMeta(
    'teacherName',
  );
  @override
  late final GeneratedColumn<String> teacherName = GeneratedColumn<String>(
    'teacher_name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    groupId,
    weekday,
    pairNumber,
    startsAt,
    endsAt,
    subject,
    room,
    weekType,
    subgroup,
    teacherName,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_lessons';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedLesson> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('group_id')) {
      context.handle(
        _groupIdMeta,
        groupId.isAcceptableOrUnknown(data['group_id']!, _groupIdMeta),
      );
    } else if (isInserting) {
      context.missing(_groupIdMeta);
    }
    if (data.containsKey('weekday')) {
      context.handle(
        _weekdayMeta,
        weekday.isAcceptableOrUnknown(data['weekday']!, _weekdayMeta),
      );
    } else if (isInserting) {
      context.missing(_weekdayMeta);
    }
    if (data.containsKey('pair_number')) {
      context.handle(
        _pairNumberMeta,
        pairNumber.isAcceptableOrUnknown(data['pair_number']!, _pairNumberMeta),
      );
    } else if (isInserting) {
      context.missing(_pairNumberMeta);
    }
    if (data.containsKey('starts_at')) {
      context.handle(
        _startsAtMeta,
        startsAt.isAcceptableOrUnknown(data['starts_at']!, _startsAtMeta),
      );
    } else if (isInserting) {
      context.missing(_startsAtMeta);
    }
    if (data.containsKey('ends_at')) {
      context.handle(
        _endsAtMeta,
        endsAt.isAcceptableOrUnknown(data['ends_at']!, _endsAtMeta),
      );
    } else if (isInserting) {
      context.missing(_endsAtMeta);
    }
    if (data.containsKey('subject')) {
      context.handle(
        _subjectMeta,
        subject.isAcceptableOrUnknown(data['subject']!, _subjectMeta),
      );
    } else if (isInserting) {
      context.missing(_subjectMeta);
    }
    if (data.containsKey('room')) {
      context.handle(
        _roomMeta,
        room.isAcceptableOrUnknown(data['room']!, _roomMeta),
      );
    }
    if (data.containsKey('week_type')) {
      context.handle(
        _weekTypeMeta,
        weekType.isAcceptableOrUnknown(data['week_type']!, _weekTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_weekTypeMeta);
    }
    if (data.containsKey('subgroup')) {
      context.handle(
        _subgroupMeta,
        subgroup.isAcceptableOrUnknown(data['subgroup']!, _subgroupMeta),
      );
    } else if (isInserting) {
      context.missing(_subgroupMeta);
    }
    if (data.containsKey('teacher_name')) {
      context.handle(
        _teacherNameMeta,
        teacherName.isAcceptableOrUnknown(
          data['teacher_name']!,
          _teacherNameMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedLesson map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedLesson(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      groupId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}group_id'],
      )!,
      weekday: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}weekday'],
      )!,
      pairNumber: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}pair_number'],
      )!,
      startsAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}starts_at'],
      )!,
      endsAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}ends_at'],
      )!,
      subject: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}subject'],
      )!,
      room: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}room'],
      ),
      weekType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}week_type'],
      )!,
      subgroup: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}subgroup'],
      )!,
      teacherName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}teacher_name'],
      ),
    );
  }

  @override
  $CachedLessonsTable createAlias(String alias) {
    return $CachedLessonsTable(attachedDatabase, alias);
  }
}

class CachedLesson extends DataClass implements Insertable<CachedLesson> {
  final int id;
  final int groupId;
  final int weekday;
  final int pairNumber;
  final String startsAt;
  final String endsAt;
  final String subject;
  final String? room;
  final String weekType;
  final int subgroup;
  final String? teacherName;
  const CachedLesson({
    required this.id,
    required this.groupId,
    required this.weekday,
    required this.pairNumber,
    required this.startsAt,
    required this.endsAt,
    required this.subject,
    this.room,
    required this.weekType,
    required this.subgroup,
    this.teacherName,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['group_id'] = Variable<int>(groupId);
    map['weekday'] = Variable<int>(weekday);
    map['pair_number'] = Variable<int>(pairNumber);
    map['starts_at'] = Variable<String>(startsAt);
    map['ends_at'] = Variable<String>(endsAt);
    map['subject'] = Variable<String>(subject);
    if (!nullToAbsent || room != null) {
      map['room'] = Variable<String>(room);
    }
    map['week_type'] = Variable<String>(weekType);
    map['subgroup'] = Variable<int>(subgroup);
    if (!nullToAbsent || teacherName != null) {
      map['teacher_name'] = Variable<String>(teacherName);
    }
    return map;
  }

  CachedLessonsCompanion toCompanion(bool nullToAbsent) {
    return CachedLessonsCompanion(
      id: Value(id),
      groupId: Value(groupId),
      weekday: Value(weekday),
      pairNumber: Value(pairNumber),
      startsAt: Value(startsAt),
      endsAt: Value(endsAt),
      subject: Value(subject),
      room: room == null && nullToAbsent ? const Value.absent() : Value(room),
      weekType: Value(weekType),
      subgroup: Value(subgroup),
      teacherName: teacherName == null && nullToAbsent
          ? const Value.absent()
          : Value(teacherName),
    );
  }

  factory CachedLesson.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedLesson(
      id: serializer.fromJson<int>(json['id']),
      groupId: serializer.fromJson<int>(json['groupId']),
      weekday: serializer.fromJson<int>(json['weekday']),
      pairNumber: serializer.fromJson<int>(json['pairNumber']),
      startsAt: serializer.fromJson<String>(json['startsAt']),
      endsAt: serializer.fromJson<String>(json['endsAt']),
      subject: serializer.fromJson<String>(json['subject']),
      room: serializer.fromJson<String?>(json['room']),
      weekType: serializer.fromJson<String>(json['weekType']),
      subgroup: serializer.fromJson<int>(json['subgroup']),
      teacherName: serializer.fromJson<String?>(json['teacherName']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'groupId': serializer.toJson<int>(groupId),
      'weekday': serializer.toJson<int>(weekday),
      'pairNumber': serializer.toJson<int>(pairNumber),
      'startsAt': serializer.toJson<String>(startsAt),
      'endsAt': serializer.toJson<String>(endsAt),
      'subject': serializer.toJson<String>(subject),
      'room': serializer.toJson<String?>(room),
      'weekType': serializer.toJson<String>(weekType),
      'subgroup': serializer.toJson<int>(subgroup),
      'teacherName': serializer.toJson<String?>(teacherName),
    };
  }

  CachedLesson copyWith({
    int? id,
    int? groupId,
    int? weekday,
    int? pairNumber,
    String? startsAt,
    String? endsAt,
    String? subject,
    Value<String?> room = const Value.absent(),
    String? weekType,
    int? subgroup,
    Value<String?> teacherName = const Value.absent(),
  }) => CachedLesson(
    id: id ?? this.id,
    groupId: groupId ?? this.groupId,
    weekday: weekday ?? this.weekday,
    pairNumber: pairNumber ?? this.pairNumber,
    startsAt: startsAt ?? this.startsAt,
    endsAt: endsAt ?? this.endsAt,
    subject: subject ?? this.subject,
    room: room.present ? room.value : this.room,
    weekType: weekType ?? this.weekType,
    subgroup: subgroup ?? this.subgroup,
    teacherName: teacherName.present ? teacherName.value : this.teacherName,
  );
  CachedLesson copyWithCompanion(CachedLessonsCompanion data) {
    return CachedLesson(
      id: data.id.present ? data.id.value : this.id,
      groupId: data.groupId.present ? data.groupId.value : this.groupId,
      weekday: data.weekday.present ? data.weekday.value : this.weekday,
      pairNumber: data.pairNumber.present
          ? data.pairNumber.value
          : this.pairNumber,
      startsAt: data.startsAt.present ? data.startsAt.value : this.startsAt,
      endsAt: data.endsAt.present ? data.endsAt.value : this.endsAt,
      subject: data.subject.present ? data.subject.value : this.subject,
      room: data.room.present ? data.room.value : this.room,
      weekType: data.weekType.present ? data.weekType.value : this.weekType,
      subgroup: data.subgroup.present ? data.subgroup.value : this.subgroup,
      teacherName: data.teacherName.present
          ? data.teacherName.value
          : this.teacherName,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedLesson(')
          ..write('id: $id, ')
          ..write('groupId: $groupId, ')
          ..write('weekday: $weekday, ')
          ..write('pairNumber: $pairNumber, ')
          ..write('startsAt: $startsAt, ')
          ..write('endsAt: $endsAt, ')
          ..write('subject: $subject, ')
          ..write('room: $room, ')
          ..write('weekType: $weekType, ')
          ..write('subgroup: $subgroup, ')
          ..write('teacherName: $teacherName')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    groupId,
    weekday,
    pairNumber,
    startsAt,
    endsAt,
    subject,
    room,
    weekType,
    subgroup,
    teacherName,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedLesson &&
          other.id == this.id &&
          other.groupId == this.groupId &&
          other.weekday == this.weekday &&
          other.pairNumber == this.pairNumber &&
          other.startsAt == this.startsAt &&
          other.endsAt == this.endsAt &&
          other.subject == this.subject &&
          other.room == this.room &&
          other.weekType == this.weekType &&
          other.subgroup == this.subgroup &&
          other.teacherName == this.teacherName);
}

class CachedLessonsCompanion extends UpdateCompanion<CachedLesson> {
  final Value<int> id;
  final Value<int> groupId;
  final Value<int> weekday;
  final Value<int> pairNumber;
  final Value<String> startsAt;
  final Value<String> endsAt;
  final Value<String> subject;
  final Value<String?> room;
  final Value<String> weekType;
  final Value<int> subgroup;
  final Value<String?> teacherName;
  const CachedLessonsCompanion({
    this.id = const Value.absent(),
    this.groupId = const Value.absent(),
    this.weekday = const Value.absent(),
    this.pairNumber = const Value.absent(),
    this.startsAt = const Value.absent(),
    this.endsAt = const Value.absent(),
    this.subject = const Value.absent(),
    this.room = const Value.absent(),
    this.weekType = const Value.absent(),
    this.subgroup = const Value.absent(),
    this.teacherName = const Value.absent(),
  });
  CachedLessonsCompanion.insert({
    this.id = const Value.absent(),
    required int groupId,
    required int weekday,
    required int pairNumber,
    required String startsAt,
    required String endsAt,
    required String subject,
    this.room = const Value.absent(),
    required String weekType,
    required int subgroup,
    this.teacherName = const Value.absent(),
  }) : groupId = Value(groupId),
       weekday = Value(weekday),
       pairNumber = Value(pairNumber),
       startsAt = Value(startsAt),
       endsAt = Value(endsAt),
       subject = Value(subject),
       weekType = Value(weekType),
       subgroup = Value(subgroup);
  static Insertable<CachedLesson> custom({
    Expression<int>? id,
    Expression<int>? groupId,
    Expression<int>? weekday,
    Expression<int>? pairNumber,
    Expression<String>? startsAt,
    Expression<String>? endsAt,
    Expression<String>? subject,
    Expression<String>? room,
    Expression<String>? weekType,
    Expression<int>? subgroup,
    Expression<String>? teacherName,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (groupId != null) 'group_id': groupId,
      if (weekday != null) 'weekday': weekday,
      if (pairNumber != null) 'pair_number': pairNumber,
      if (startsAt != null) 'starts_at': startsAt,
      if (endsAt != null) 'ends_at': endsAt,
      if (subject != null) 'subject': subject,
      if (room != null) 'room': room,
      if (weekType != null) 'week_type': weekType,
      if (subgroup != null) 'subgroup': subgroup,
      if (teacherName != null) 'teacher_name': teacherName,
    });
  }

  CachedLessonsCompanion copyWith({
    Value<int>? id,
    Value<int>? groupId,
    Value<int>? weekday,
    Value<int>? pairNumber,
    Value<String>? startsAt,
    Value<String>? endsAt,
    Value<String>? subject,
    Value<String?>? room,
    Value<String>? weekType,
    Value<int>? subgroup,
    Value<String?>? teacherName,
  }) {
    return CachedLessonsCompanion(
      id: id ?? this.id,
      groupId: groupId ?? this.groupId,
      weekday: weekday ?? this.weekday,
      pairNumber: pairNumber ?? this.pairNumber,
      startsAt: startsAt ?? this.startsAt,
      endsAt: endsAt ?? this.endsAt,
      subject: subject ?? this.subject,
      room: room ?? this.room,
      weekType: weekType ?? this.weekType,
      subgroup: subgroup ?? this.subgroup,
      teacherName: teacherName ?? this.teacherName,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (groupId.present) {
      map['group_id'] = Variable<int>(groupId.value);
    }
    if (weekday.present) {
      map['weekday'] = Variable<int>(weekday.value);
    }
    if (pairNumber.present) {
      map['pair_number'] = Variable<int>(pairNumber.value);
    }
    if (startsAt.present) {
      map['starts_at'] = Variable<String>(startsAt.value);
    }
    if (endsAt.present) {
      map['ends_at'] = Variable<String>(endsAt.value);
    }
    if (subject.present) {
      map['subject'] = Variable<String>(subject.value);
    }
    if (room.present) {
      map['room'] = Variable<String>(room.value);
    }
    if (weekType.present) {
      map['week_type'] = Variable<String>(weekType.value);
    }
    if (subgroup.present) {
      map['subgroup'] = Variable<int>(subgroup.value);
    }
    if (teacherName.present) {
      map['teacher_name'] = Variable<String>(teacherName.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedLessonsCompanion(')
          ..write('id: $id, ')
          ..write('groupId: $groupId, ')
          ..write('weekday: $weekday, ')
          ..write('pairNumber: $pairNumber, ')
          ..write('startsAt: $startsAt, ')
          ..write('endsAt: $endsAt, ')
          ..write('subject: $subject, ')
          ..write('room: $room, ')
          ..write('weekType: $weekType, ')
          ..write('subgroup: $subgroup, ')
          ..write('teacherName: $teacherName')
          ..write(')'))
        .toString();
  }
}

class $ScheduleCacheMetaTable extends ScheduleCacheMeta
    with TableInfo<$ScheduleCacheMetaTable, ScheduleCacheMetaData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ScheduleCacheMetaTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _groupIdMeta = const VerificationMeta(
    'groupId',
  );
  @override
  late final GeneratedColumn<int> groupId = GeneratedColumn<int>(
    'group_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _etagMeta = const VerificationMeta('etag');
  @override
  late final GeneratedColumn<String> etag = GeneratedColumn<String>(
    'etag',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _syncedAtMeta = const VerificationMeta(
    'syncedAt',
  );
  @override
  late final GeneratedColumn<DateTime> syncedAt = GeneratedColumn<DateTime>(
    'synced_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [groupId, etag, syncedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'schedule_cache_meta';
  @override
  VerificationContext validateIntegrity(
    Insertable<ScheduleCacheMetaData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('group_id')) {
      context.handle(
        _groupIdMeta,
        groupId.isAcceptableOrUnknown(data['group_id']!, _groupIdMeta),
      );
    }
    if (data.containsKey('etag')) {
      context.handle(
        _etagMeta,
        etag.isAcceptableOrUnknown(data['etag']!, _etagMeta),
      );
    }
    if (data.containsKey('synced_at')) {
      context.handle(
        _syncedAtMeta,
        syncedAt.isAcceptableOrUnknown(data['synced_at']!, _syncedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_syncedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {groupId};
  @override
  ScheduleCacheMetaData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ScheduleCacheMetaData(
      groupId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}group_id'],
      )!,
      etag: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}etag'],
      ),
      syncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}synced_at'],
      )!,
    );
  }

  @override
  $ScheduleCacheMetaTable createAlias(String alias) {
    return $ScheduleCacheMetaTable(attachedDatabase, alias);
  }
}

class ScheduleCacheMetaData extends DataClass
    implements Insertable<ScheduleCacheMetaData> {
  final int groupId;
  final String? etag;
  final DateTime syncedAt;
  const ScheduleCacheMetaData({
    required this.groupId,
    this.etag,
    required this.syncedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['group_id'] = Variable<int>(groupId);
    if (!nullToAbsent || etag != null) {
      map['etag'] = Variable<String>(etag);
    }
    map['synced_at'] = Variable<DateTime>(syncedAt);
    return map;
  }

  ScheduleCacheMetaCompanion toCompanion(bool nullToAbsent) {
    return ScheduleCacheMetaCompanion(
      groupId: Value(groupId),
      etag: etag == null && nullToAbsent ? const Value.absent() : Value(etag),
      syncedAt: Value(syncedAt),
    );
  }

  factory ScheduleCacheMetaData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ScheduleCacheMetaData(
      groupId: serializer.fromJson<int>(json['groupId']),
      etag: serializer.fromJson<String?>(json['etag']),
      syncedAt: serializer.fromJson<DateTime>(json['syncedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'groupId': serializer.toJson<int>(groupId),
      'etag': serializer.toJson<String?>(etag),
      'syncedAt': serializer.toJson<DateTime>(syncedAt),
    };
  }

  ScheduleCacheMetaData copyWith({
    int? groupId,
    Value<String?> etag = const Value.absent(),
    DateTime? syncedAt,
  }) => ScheduleCacheMetaData(
    groupId: groupId ?? this.groupId,
    etag: etag.present ? etag.value : this.etag,
    syncedAt: syncedAt ?? this.syncedAt,
  );
  ScheduleCacheMetaData copyWithCompanion(ScheduleCacheMetaCompanion data) {
    return ScheduleCacheMetaData(
      groupId: data.groupId.present ? data.groupId.value : this.groupId,
      etag: data.etag.present ? data.etag.value : this.etag,
      syncedAt: data.syncedAt.present ? data.syncedAt.value : this.syncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ScheduleCacheMetaData(')
          ..write('groupId: $groupId, ')
          ..write('etag: $etag, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(groupId, etag, syncedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ScheduleCacheMetaData &&
          other.groupId == this.groupId &&
          other.etag == this.etag &&
          other.syncedAt == this.syncedAt);
}

class ScheduleCacheMetaCompanion
    extends UpdateCompanion<ScheduleCacheMetaData> {
  final Value<int> groupId;
  final Value<String?> etag;
  final Value<DateTime> syncedAt;
  const ScheduleCacheMetaCompanion({
    this.groupId = const Value.absent(),
    this.etag = const Value.absent(),
    this.syncedAt = const Value.absent(),
  });
  ScheduleCacheMetaCompanion.insert({
    this.groupId = const Value.absent(),
    this.etag = const Value.absent(),
    required DateTime syncedAt,
  }) : syncedAt = Value(syncedAt);
  static Insertable<ScheduleCacheMetaData> custom({
    Expression<int>? groupId,
    Expression<String>? etag,
    Expression<DateTime>? syncedAt,
  }) {
    return RawValuesInsertable({
      if (groupId != null) 'group_id': groupId,
      if (etag != null) 'etag': etag,
      if (syncedAt != null) 'synced_at': syncedAt,
    });
  }

  ScheduleCacheMetaCompanion copyWith({
    Value<int>? groupId,
    Value<String?>? etag,
    Value<DateTime>? syncedAt,
  }) {
    return ScheduleCacheMetaCompanion(
      groupId: groupId ?? this.groupId,
      etag: etag ?? this.etag,
      syncedAt: syncedAt ?? this.syncedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (groupId.present) {
      map['group_id'] = Variable<int>(groupId.value);
    }
    if (etag.present) {
      map['etag'] = Variable<String>(etag.value);
    }
    if (syncedAt.present) {
      map['synced_at'] = Variable<DateTime>(syncedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ScheduleCacheMetaCompanion(')
          ..write('groupId: $groupId, ')
          ..write('etag: $etag, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $CachedLessonsTable cachedLessons = $CachedLessonsTable(this);
  late final $ScheduleCacheMetaTable scheduleCacheMeta =
      $ScheduleCacheMetaTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    cachedLessons,
    scheduleCacheMeta,
  ];
}

typedef $$CachedLessonsTableCreateCompanionBuilder =
    CachedLessonsCompanion Function({
      Value<int> id,
      required int groupId,
      required int weekday,
      required int pairNumber,
      required String startsAt,
      required String endsAt,
      required String subject,
      Value<String?> room,
      required String weekType,
      required int subgroup,
      Value<String?> teacherName,
    });
typedef $$CachedLessonsTableUpdateCompanionBuilder =
    CachedLessonsCompanion Function({
      Value<int> id,
      Value<int> groupId,
      Value<int> weekday,
      Value<int> pairNumber,
      Value<String> startsAt,
      Value<String> endsAt,
      Value<String> subject,
      Value<String?> room,
      Value<String> weekType,
      Value<int> subgroup,
      Value<String?> teacherName,
    });

class $$CachedLessonsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedLessonsTable> {
  $$CachedLessonsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get groupId => $composableBuilder(
    column: $table.groupId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get weekday => $composableBuilder(
    column: $table.weekday,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get pairNumber => $composableBuilder(
    column: $table.pairNumber,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get startsAt => $composableBuilder(
    column: $table.startsAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get endsAt => $composableBuilder(
    column: $table.endsAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get subject => $composableBuilder(
    column: $table.subject,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get room => $composableBuilder(
    column: $table.room,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get weekType => $composableBuilder(
    column: $table.weekType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get subgroup => $composableBuilder(
    column: $table.subgroup,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get teacherName => $composableBuilder(
    column: $table.teacherName,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedLessonsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedLessonsTable> {
  $$CachedLessonsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get groupId => $composableBuilder(
    column: $table.groupId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get weekday => $composableBuilder(
    column: $table.weekday,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get pairNumber => $composableBuilder(
    column: $table.pairNumber,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get startsAt => $composableBuilder(
    column: $table.startsAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get endsAt => $composableBuilder(
    column: $table.endsAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get subject => $composableBuilder(
    column: $table.subject,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get room => $composableBuilder(
    column: $table.room,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get weekType => $composableBuilder(
    column: $table.weekType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get subgroup => $composableBuilder(
    column: $table.subgroup,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get teacherName => $composableBuilder(
    column: $table.teacherName,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedLessonsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedLessonsTable> {
  $$CachedLessonsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get groupId =>
      $composableBuilder(column: $table.groupId, builder: (column) => column);

  GeneratedColumn<int> get weekday =>
      $composableBuilder(column: $table.weekday, builder: (column) => column);

  GeneratedColumn<int> get pairNumber => $composableBuilder(
    column: $table.pairNumber,
    builder: (column) => column,
  );

  GeneratedColumn<String> get startsAt =>
      $composableBuilder(column: $table.startsAt, builder: (column) => column);

  GeneratedColumn<String> get endsAt =>
      $composableBuilder(column: $table.endsAt, builder: (column) => column);

  GeneratedColumn<String> get subject =>
      $composableBuilder(column: $table.subject, builder: (column) => column);

  GeneratedColumn<String> get room =>
      $composableBuilder(column: $table.room, builder: (column) => column);

  GeneratedColumn<String> get weekType =>
      $composableBuilder(column: $table.weekType, builder: (column) => column);

  GeneratedColumn<int> get subgroup =>
      $composableBuilder(column: $table.subgroup, builder: (column) => column);

  GeneratedColumn<String> get teacherName => $composableBuilder(
    column: $table.teacherName,
    builder: (column) => column,
  );
}

class $$CachedLessonsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedLessonsTable,
          CachedLesson,
          $$CachedLessonsTableFilterComposer,
          $$CachedLessonsTableOrderingComposer,
          $$CachedLessonsTableAnnotationComposer,
          $$CachedLessonsTableCreateCompanionBuilder,
          $$CachedLessonsTableUpdateCompanionBuilder,
          (
            CachedLesson,
            BaseReferences<_$AppDatabase, $CachedLessonsTable, CachedLesson>,
          ),
          CachedLesson,
          PrefetchHooks Function()
        > {
  $$CachedLessonsTableTableManager(_$AppDatabase db, $CachedLessonsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedLessonsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedLessonsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedLessonsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> groupId = const Value.absent(),
                Value<int> weekday = const Value.absent(),
                Value<int> pairNumber = const Value.absent(),
                Value<String> startsAt = const Value.absent(),
                Value<String> endsAt = const Value.absent(),
                Value<String> subject = const Value.absent(),
                Value<String?> room = const Value.absent(),
                Value<String> weekType = const Value.absent(),
                Value<int> subgroup = const Value.absent(),
                Value<String?> teacherName = const Value.absent(),
              }) => CachedLessonsCompanion(
                id: id,
                groupId: groupId,
                weekday: weekday,
                pairNumber: pairNumber,
                startsAt: startsAt,
                endsAt: endsAt,
                subject: subject,
                room: room,
                weekType: weekType,
                subgroup: subgroup,
                teacherName: teacherName,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int groupId,
                required int weekday,
                required int pairNumber,
                required String startsAt,
                required String endsAt,
                required String subject,
                Value<String?> room = const Value.absent(),
                required String weekType,
                required int subgroup,
                Value<String?> teacherName = const Value.absent(),
              }) => CachedLessonsCompanion.insert(
                id: id,
                groupId: groupId,
                weekday: weekday,
                pairNumber: pairNumber,
                startsAt: startsAt,
                endsAt: endsAt,
                subject: subject,
                room: room,
                weekType: weekType,
                subgroup: subgroup,
                teacherName: teacherName,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedLessonsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedLessonsTable,
      CachedLesson,
      $$CachedLessonsTableFilterComposer,
      $$CachedLessonsTableOrderingComposer,
      $$CachedLessonsTableAnnotationComposer,
      $$CachedLessonsTableCreateCompanionBuilder,
      $$CachedLessonsTableUpdateCompanionBuilder,
      (
        CachedLesson,
        BaseReferences<_$AppDatabase, $CachedLessonsTable, CachedLesson>,
      ),
      CachedLesson,
      PrefetchHooks Function()
    >;
typedef $$ScheduleCacheMetaTableCreateCompanionBuilder =
    ScheduleCacheMetaCompanion Function({
      Value<int> groupId,
      Value<String?> etag,
      required DateTime syncedAt,
    });
typedef $$ScheduleCacheMetaTableUpdateCompanionBuilder =
    ScheduleCacheMetaCompanion Function({
      Value<int> groupId,
      Value<String?> etag,
      Value<DateTime> syncedAt,
    });

class $$ScheduleCacheMetaTableFilterComposer
    extends Composer<_$AppDatabase, $ScheduleCacheMetaTable> {
  $$ScheduleCacheMetaTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get groupId => $composableBuilder(
    column: $table.groupId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get etag => $composableBuilder(
    column: $table.etag,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get syncedAt => $composableBuilder(
    column: $table.syncedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ScheduleCacheMetaTableOrderingComposer
    extends Composer<_$AppDatabase, $ScheduleCacheMetaTable> {
  $$ScheduleCacheMetaTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get groupId => $composableBuilder(
    column: $table.groupId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get etag => $composableBuilder(
    column: $table.etag,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get syncedAt => $composableBuilder(
    column: $table.syncedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ScheduleCacheMetaTableAnnotationComposer
    extends Composer<_$AppDatabase, $ScheduleCacheMetaTable> {
  $$ScheduleCacheMetaTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get groupId =>
      $composableBuilder(column: $table.groupId, builder: (column) => column);

  GeneratedColumn<String> get etag =>
      $composableBuilder(column: $table.etag, builder: (column) => column);

  GeneratedColumn<DateTime> get syncedAt =>
      $composableBuilder(column: $table.syncedAt, builder: (column) => column);
}

class $$ScheduleCacheMetaTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ScheduleCacheMetaTable,
          ScheduleCacheMetaData,
          $$ScheduleCacheMetaTableFilterComposer,
          $$ScheduleCacheMetaTableOrderingComposer,
          $$ScheduleCacheMetaTableAnnotationComposer,
          $$ScheduleCacheMetaTableCreateCompanionBuilder,
          $$ScheduleCacheMetaTableUpdateCompanionBuilder,
          (
            ScheduleCacheMetaData,
            BaseReferences<
              _$AppDatabase,
              $ScheduleCacheMetaTable,
              ScheduleCacheMetaData
            >,
          ),
          ScheduleCacheMetaData,
          PrefetchHooks Function()
        > {
  $$ScheduleCacheMetaTableTableManager(
    _$AppDatabase db,
    $ScheduleCacheMetaTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ScheduleCacheMetaTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ScheduleCacheMetaTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ScheduleCacheMetaTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> groupId = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                Value<DateTime> syncedAt = const Value.absent(),
              }) => ScheduleCacheMetaCompanion(
                groupId: groupId,
                etag: etag,
                syncedAt: syncedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> groupId = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                required DateTime syncedAt,
              }) => ScheduleCacheMetaCompanion.insert(
                groupId: groupId,
                etag: etag,
                syncedAt: syncedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ScheduleCacheMetaTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ScheduleCacheMetaTable,
      ScheduleCacheMetaData,
      $$ScheduleCacheMetaTableFilterComposer,
      $$ScheduleCacheMetaTableOrderingComposer,
      $$ScheduleCacheMetaTableAnnotationComposer,
      $$ScheduleCacheMetaTableCreateCompanionBuilder,
      $$ScheduleCacheMetaTableUpdateCompanionBuilder,
      (
        ScheduleCacheMetaData,
        BaseReferences<
          _$AppDatabase,
          $ScheduleCacheMetaTable,
          ScheduleCacheMetaData
        >,
      ),
      ScheduleCacheMetaData,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$CachedLessonsTableTableManager get cachedLessons =>
      $$CachedLessonsTableTableManager(_db, _db.cachedLessons);
  $$ScheduleCacheMetaTableTableManager get scheduleCacheMeta =>
      $$ScheduleCacheMetaTableTableManager(_db, _db.scheduleCacheMeta);
}
