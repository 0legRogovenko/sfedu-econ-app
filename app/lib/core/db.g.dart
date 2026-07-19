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
    requiredDuringInsert: true,
  );
  static const VerificationMeta _scopeMeta = const VerificationMeta('scope');
  @override
  late final GeneratedColumn<String> scope = GeneratedColumn<String>(
    'scope',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
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
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
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
  static const VerificationMeta _moduleIdMeta = const VerificationMeta(
    'moduleId',
  );
  @override
  late final GeneratedColumn<int> moduleId = GeneratedColumn<int>(
    'module_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _validFromMeta = const VerificationMeta(
    'validFrom',
  );
  @override
  late final GeneratedColumn<String> validFrom = GeneratedColumn<String>(
    'valid_from',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _validToMeta = const VerificationMeta(
    'validTo',
  );
  @override
  late final GeneratedColumn<String> validTo = GeneratedColumn<String>(
    'valid_to',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    scope,
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
    moduleId,
    validFrom,
    validTo,
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
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('scope')) {
      context.handle(
        _scopeMeta,
        scope.isAcceptableOrUnknown(data['scope']!, _scopeMeta),
      );
    } else if (isInserting) {
      context.missing(_scopeMeta);
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
    if (data.containsKey('module_id')) {
      context.handle(
        _moduleIdMeta,
        moduleId.isAcceptableOrUnknown(data['module_id']!, _moduleIdMeta),
      );
    }
    if (data.containsKey('valid_from')) {
      context.handle(
        _validFromMeta,
        validFrom.isAcceptableOrUnknown(data['valid_from']!, _validFromMeta),
      );
    }
    if (data.containsKey('valid_to')) {
      context.handle(
        _validToMeta,
        validTo.isAcceptableOrUnknown(data['valid_to']!, _validToMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {scope, id};
  @override
  CachedLesson map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedLesson(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      scope: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}scope'],
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
      ),
      subgroup: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}subgroup'],
      )!,
      teacherName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}teacher_name'],
      ),
      moduleId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}module_id'],
      ),
      validFrom: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}valid_from'],
      ),
      validTo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}valid_to'],
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

  /// Чей это кэш: 'group:3' или 'teacher:7' (см. ScheduleScope). Отдельно от
  /// [groupId], который остаётся СВОЙСТВОМ ПАРЫ: в расписании преподавателя
  /// именно он подписывает карточку.
  final String scope;
  final int groupId;
  final int weekday;
  final int pairNumber;
  final String startsAt;
  final String endsAt;
  final String subject;
  final String? room;
  final String? weekType;
  final int subgroup;
  final String? teacherName;
  final int? moduleId;
  final String? validFrom;
  final String? validTo;
  const CachedLesson({
    required this.id,
    required this.scope,
    required this.groupId,
    required this.weekday,
    required this.pairNumber,
    required this.startsAt,
    required this.endsAt,
    required this.subject,
    this.room,
    this.weekType,
    required this.subgroup,
    this.teacherName,
    this.moduleId,
    this.validFrom,
    this.validTo,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['scope'] = Variable<String>(scope);
    map['group_id'] = Variable<int>(groupId);
    map['weekday'] = Variable<int>(weekday);
    map['pair_number'] = Variable<int>(pairNumber);
    map['starts_at'] = Variable<String>(startsAt);
    map['ends_at'] = Variable<String>(endsAt);
    map['subject'] = Variable<String>(subject);
    if (!nullToAbsent || room != null) {
      map['room'] = Variable<String>(room);
    }
    if (!nullToAbsent || weekType != null) {
      map['week_type'] = Variable<String>(weekType);
    }
    map['subgroup'] = Variable<int>(subgroup);
    if (!nullToAbsent || teacherName != null) {
      map['teacher_name'] = Variable<String>(teacherName);
    }
    if (!nullToAbsent || moduleId != null) {
      map['module_id'] = Variable<int>(moduleId);
    }
    if (!nullToAbsent || validFrom != null) {
      map['valid_from'] = Variable<String>(validFrom);
    }
    if (!nullToAbsent || validTo != null) {
      map['valid_to'] = Variable<String>(validTo);
    }
    return map;
  }

  CachedLessonsCompanion toCompanion(bool nullToAbsent) {
    return CachedLessonsCompanion(
      id: Value(id),
      scope: Value(scope),
      groupId: Value(groupId),
      weekday: Value(weekday),
      pairNumber: Value(pairNumber),
      startsAt: Value(startsAt),
      endsAt: Value(endsAt),
      subject: Value(subject),
      room: room == null && nullToAbsent ? const Value.absent() : Value(room),
      weekType: weekType == null && nullToAbsent
          ? const Value.absent()
          : Value(weekType),
      subgroup: Value(subgroup),
      teacherName: teacherName == null && nullToAbsent
          ? const Value.absent()
          : Value(teacherName),
      moduleId: moduleId == null && nullToAbsent
          ? const Value.absent()
          : Value(moduleId),
      validFrom: validFrom == null && nullToAbsent
          ? const Value.absent()
          : Value(validFrom),
      validTo: validTo == null && nullToAbsent
          ? const Value.absent()
          : Value(validTo),
    );
  }

  factory CachedLesson.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedLesson(
      id: serializer.fromJson<int>(json['id']),
      scope: serializer.fromJson<String>(json['scope']),
      groupId: serializer.fromJson<int>(json['groupId']),
      weekday: serializer.fromJson<int>(json['weekday']),
      pairNumber: serializer.fromJson<int>(json['pairNumber']),
      startsAt: serializer.fromJson<String>(json['startsAt']),
      endsAt: serializer.fromJson<String>(json['endsAt']),
      subject: serializer.fromJson<String>(json['subject']),
      room: serializer.fromJson<String?>(json['room']),
      weekType: serializer.fromJson<String?>(json['weekType']),
      subgroup: serializer.fromJson<int>(json['subgroup']),
      teacherName: serializer.fromJson<String?>(json['teacherName']),
      moduleId: serializer.fromJson<int?>(json['moduleId']),
      validFrom: serializer.fromJson<String?>(json['validFrom']),
      validTo: serializer.fromJson<String?>(json['validTo']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'scope': serializer.toJson<String>(scope),
      'groupId': serializer.toJson<int>(groupId),
      'weekday': serializer.toJson<int>(weekday),
      'pairNumber': serializer.toJson<int>(pairNumber),
      'startsAt': serializer.toJson<String>(startsAt),
      'endsAt': serializer.toJson<String>(endsAt),
      'subject': serializer.toJson<String>(subject),
      'room': serializer.toJson<String?>(room),
      'weekType': serializer.toJson<String?>(weekType),
      'subgroup': serializer.toJson<int>(subgroup),
      'teacherName': serializer.toJson<String?>(teacherName),
      'moduleId': serializer.toJson<int?>(moduleId),
      'validFrom': serializer.toJson<String?>(validFrom),
      'validTo': serializer.toJson<String?>(validTo),
    };
  }

  CachedLesson copyWith({
    int? id,
    String? scope,
    int? groupId,
    int? weekday,
    int? pairNumber,
    String? startsAt,
    String? endsAt,
    String? subject,
    Value<String?> room = const Value.absent(),
    Value<String?> weekType = const Value.absent(),
    int? subgroup,
    Value<String?> teacherName = const Value.absent(),
    Value<int?> moduleId = const Value.absent(),
    Value<String?> validFrom = const Value.absent(),
    Value<String?> validTo = const Value.absent(),
  }) => CachedLesson(
    id: id ?? this.id,
    scope: scope ?? this.scope,
    groupId: groupId ?? this.groupId,
    weekday: weekday ?? this.weekday,
    pairNumber: pairNumber ?? this.pairNumber,
    startsAt: startsAt ?? this.startsAt,
    endsAt: endsAt ?? this.endsAt,
    subject: subject ?? this.subject,
    room: room.present ? room.value : this.room,
    weekType: weekType.present ? weekType.value : this.weekType,
    subgroup: subgroup ?? this.subgroup,
    teacherName: teacherName.present ? teacherName.value : this.teacherName,
    moduleId: moduleId.present ? moduleId.value : this.moduleId,
    validFrom: validFrom.present ? validFrom.value : this.validFrom,
    validTo: validTo.present ? validTo.value : this.validTo,
  );
  CachedLesson copyWithCompanion(CachedLessonsCompanion data) {
    return CachedLesson(
      id: data.id.present ? data.id.value : this.id,
      scope: data.scope.present ? data.scope.value : this.scope,
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
      moduleId: data.moduleId.present ? data.moduleId.value : this.moduleId,
      validFrom: data.validFrom.present ? data.validFrom.value : this.validFrom,
      validTo: data.validTo.present ? data.validTo.value : this.validTo,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedLesson(')
          ..write('id: $id, ')
          ..write('scope: $scope, ')
          ..write('groupId: $groupId, ')
          ..write('weekday: $weekday, ')
          ..write('pairNumber: $pairNumber, ')
          ..write('startsAt: $startsAt, ')
          ..write('endsAt: $endsAt, ')
          ..write('subject: $subject, ')
          ..write('room: $room, ')
          ..write('weekType: $weekType, ')
          ..write('subgroup: $subgroup, ')
          ..write('teacherName: $teacherName, ')
          ..write('moduleId: $moduleId, ')
          ..write('validFrom: $validFrom, ')
          ..write('validTo: $validTo')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    scope,
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
    moduleId,
    validFrom,
    validTo,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedLesson &&
          other.id == this.id &&
          other.scope == this.scope &&
          other.groupId == this.groupId &&
          other.weekday == this.weekday &&
          other.pairNumber == this.pairNumber &&
          other.startsAt == this.startsAt &&
          other.endsAt == this.endsAt &&
          other.subject == this.subject &&
          other.room == this.room &&
          other.weekType == this.weekType &&
          other.subgroup == this.subgroup &&
          other.teacherName == this.teacherName &&
          other.moduleId == this.moduleId &&
          other.validFrom == this.validFrom &&
          other.validTo == this.validTo);
}

class CachedLessonsCompanion extends UpdateCompanion<CachedLesson> {
  final Value<int> id;
  final Value<String> scope;
  final Value<int> groupId;
  final Value<int> weekday;
  final Value<int> pairNumber;
  final Value<String> startsAt;
  final Value<String> endsAt;
  final Value<String> subject;
  final Value<String?> room;
  final Value<String?> weekType;
  final Value<int> subgroup;
  final Value<String?> teacherName;
  final Value<int?> moduleId;
  final Value<String?> validFrom;
  final Value<String?> validTo;
  final Value<int> rowid;
  const CachedLessonsCompanion({
    this.id = const Value.absent(),
    this.scope = const Value.absent(),
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
    this.moduleId = const Value.absent(),
    this.validFrom = const Value.absent(),
    this.validTo = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedLessonsCompanion.insert({
    required int id,
    required String scope,
    required int groupId,
    required int weekday,
    required int pairNumber,
    required String startsAt,
    required String endsAt,
    required String subject,
    this.room = const Value.absent(),
    this.weekType = const Value.absent(),
    required int subgroup,
    this.teacherName = const Value.absent(),
    this.moduleId = const Value.absent(),
    this.validFrom = const Value.absent(),
    this.validTo = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       scope = Value(scope),
       groupId = Value(groupId),
       weekday = Value(weekday),
       pairNumber = Value(pairNumber),
       startsAt = Value(startsAt),
       endsAt = Value(endsAt),
       subject = Value(subject),
       subgroup = Value(subgroup);
  static Insertable<CachedLesson> custom({
    Expression<int>? id,
    Expression<String>? scope,
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
    Expression<int>? moduleId,
    Expression<String>? validFrom,
    Expression<String>? validTo,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (scope != null) 'scope': scope,
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
      if (moduleId != null) 'module_id': moduleId,
      if (validFrom != null) 'valid_from': validFrom,
      if (validTo != null) 'valid_to': validTo,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedLessonsCompanion copyWith({
    Value<int>? id,
    Value<String>? scope,
    Value<int>? groupId,
    Value<int>? weekday,
    Value<int>? pairNumber,
    Value<String>? startsAt,
    Value<String>? endsAt,
    Value<String>? subject,
    Value<String?>? room,
    Value<String?>? weekType,
    Value<int>? subgroup,
    Value<String?>? teacherName,
    Value<int?>? moduleId,
    Value<String?>? validFrom,
    Value<String?>? validTo,
    Value<int>? rowid,
  }) {
    return CachedLessonsCompanion(
      id: id ?? this.id,
      scope: scope ?? this.scope,
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
      moduleId: moduleId ?? this.moduleId,
      validFrom: validFrom ?? this.validFrom,
      validTo: validTo ?? this.validTo,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (scope.present) {
      map['scope'] = Variable<String>(scope.value);
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
    if (moduleId.present) {
      map['module_id'] = Variable<int>(moduleId.value);
    }
    if (validFrom.present) {
      map['valid_from'] = Variable<String>(validFrom.value);
    }
    if (validTo.present) {
      map['valid_to'] = Variable<String>(validTo.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedLessonsCompanion(')
          ..write('id: $id, ')
          ..write('scope: $scope, ')
          ..write('groupId: $groupId, ')
          ..write('weekday: $weekday, ')
          ..write('pairNumber: $pairNumber, ')
          ..write('startsAt: $startsAt, ')
          ..write('endsAt: $endsAt, ')
          ..write('subject: $subject, ')
          ..write('room: $room, ')
          ..write('weekType: $weekType, ')
          ..write('subgroup: $subgroup, ')
          ..write('teacherName: $teacherName, ')
          ..write('moduleId: $moduleId, ')
          ..write('validFrom: $validFrom, ')
          ..write('validTo: $validTo, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $CachedModulesTable extends CachedModules
    with TableInfo<$CachedModulesTable, CachedModule> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedModulesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _scopeMeta = const VerificationMeta('scope');
  @override
  late final GeneratedColumn<String> scope = GeneratedColumn<String>(
    'scope',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _moduleIdMeta = const VerificationMeta(
    'moduleId',
  );
  @override
  late final GeneratedColumn<int> moduleId = GeneratedColumn<int>(
    'module_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _dateFromMeta = const VerificationMeta(
    'dateFrom',
  );
  @override
  late final GeneratedColumn<String> dateFrom = GeneratedColumn<String>(
    'date_from',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dateToMeta = const VerificationMeta('dateTo');
  @override
  late final GeneratedColumn<String> dateTo = GeneratedColumn<String>(
    'date_to',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    scope,
    moduleId,
    name,
    dateFrom,
    dateTo,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_modules';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedModule> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('scope')) {
      context.handle(
        _scopeMeta,
        scope.isAcceptableOrUnknown(data['scope']!, _scopeMeta),
      );
    } else if (isInserting) {
      context.missing(_scopeMeta);
    }
    if (data.containsKey('module_id')) {
      context.handle(
        _moduleIdMeta,
        moduleId.isAcceptableOrUnknown(data['module_id']!, _moduleIdMeta),
      );
    } else if (isInserting) {
      context.missing(_moduleIdMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    }
    if (data.containsKey('date_from')) {
      context.handle(
        _dateFromMeta,
        dateFrom.isAcceptableOrUnknown(data['date_from']!, _dateFromMeta),
      );
    } else if (isInserting) {
      context.missing(_dateFromMeta);
    }
    if (data.containsKey('date_to')) {
      context.handle(
        _dateToMeta,
        dateTo.isAcceptableOrUnknown(data['date_to']!, _dateToMeta),
      );
    } else if (isInserting) {
      context.missing(_dateToMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => const {};
  @override
  CachedModule map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedModule(
      scope: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}scope'],
      )!,
      moduleId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}module_id'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      ),
      dateFrom: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}date_from'],
      )!,
      dateTo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}date_to'],
      )!,
    );
  }

  @override
  $CachedModulesTable createAlias(String alias) {
    return $CachedModulesTable(attachedDatabase, alias);
  }
}

class CachedModule extends DataClass implements Insertable<CachedModule> {
  final String scope;
  final int moduleId;
  final String? name;
  final String dateFrom;
  final String dateTo;
  const CachedModule({
    required this.scope,
    required this.moduleId,
    this.name,
    required this.dateFrom,
    required this.dateTo,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['scope'] = Variable<String>(scope);
    map['module_id'] = Variable<int>(moduleId);
    if (!nullToAbsent || name != null) {
      map['name'] = Variable<String>(name);
    }
    map['date_from'] = Variable<String>(dateFrom);
    map['date_to'] = Variable<String>(dateTo);
    return map;
  }

  CachedModulesCompanion toCompanion(bool nullToAbsent) {
    return CachedModulesCompanion(
      scope: Value(scope),
      moduleId: Value(moduleId),
      name: name == null && nullToAbsent ? const Value.absent() : Value(name),
      dateFrom: Value(dateFrom),
      dateTo: Value(dateTo),
    );
  }

  factory CachedModule.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedModule(
      scope: serializer.fromJson<String>(json['scope']),
      moduleId: serializer.fromJson<int>(json['moduleId']),
      name: serializer.fromJson<String?>(json['name']),
      dateFrom: serializer.fromJson<String>(json['dateFrom']),
      dateTo: serializer.fromJson<String>(json['dateTo']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'scope': serializer.toJson<String>(scope),
      'moduleId': serializer.toJson<int>(moduleId),
      'name': serializer.toJson<String?>(name),
      'dateFrom': serializer.toJson<String>(dateFrom),
      'dateTo': serializer.toJson<String>(dateTo),
    };
  }

  CachedModule copyWith({
    String? scope,
    int? moduleId,
    Value<String?> name = const Value.absent(),
    String? dateFrom,
    String? dateTo,
  }) => CachedModule(
    scope: scope ?? this.scope,
    moduleId: moduleId ?? this.moduleId,
    name: name.present ? name.value : this.name,
    dateFrom: dateFrom ?? this.dateFrom,
    dateTo: dateTo ?? this.dateTo,
  );
  CachedModule copyWithCompanion(CachedModulesCompanion data) {
    return CachedModule(
      scope: data.scope.present ? data.scope.value : this.scope,
      moduleId: data.moduleId.present ? data.moduleId.value : this.moduleId,
      name: data.name.present ? data.name.value : this.name,
      dateFrom: data.dateFrom.present ? data.dateFrom.value : this.dateFrom,
      dateTo: data.dateTo.present ? data.dateTo.value : this.dateTo,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedModule(')
          ..write('scope: $scope, ')
          ..write('moduleId: $moduleId, ')
          ..write('name: $name, ')
          ..write('dateFrom: $dateFrom, ')
          ..write('dateTo: $dateTo')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(scope, moduleId, name, dateFrom, dateTo);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedModule &&
          other.scope == this.scope &&
          other.moduleId == this.moduleId &&
          other.name == this.name &&
          other.dateFrom == this.dateFrom &&
          other.dateTo == this.dateTo);
}

class CachedModulesCompanion extends UpdateCompanion<CachedModule> {
  final Value<String> scope;
  final Value<int> moduleId;
  final Value<String?> name;
  final Value<String> dateFrom;
  final Value<String> dateTo;
  final Value<int> rowid;
  const CachedModulesCompanion({
    this.scope = const Value.absent(),
    this.moduleId = const Value.absent(),
    this.name = const Value.absent(),
    this.dateFrom = const Value.absent(),
    this.dateTo = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedModulesCompanion.insert({
    required String scope,
    required int moduleId,
    this.name = const Value.absent(),
    required String dateFrom,
    required String dateTo,
    this.rowid = const Value.absent(),
  }) : scope = Value(scope),
       moduleId = Value(moduleId),
       dateFrom = Value(dateFrom),
       dateTo = Value(dateTo);
  static Insertable<CachedModule> custom({
    Expression<String>? scope,
    Expression<int>? moduleId,
    Expression<String>? name,
    Expression<String>? dateFrom,
    Expression<String>? dateTo,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (scope != null) 'scope': scope,
      if (moduleId != null) 'module_id': moduleId,
      if (name != null) 'name': name,
      if (dateFrom != null) 'date_from': dateFrom,
      if (dateTo != null) 'date_to': dateTo,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedModulesCompanion copyWith({
    Value<String>? scope,
    Value<int>? moduleId,
    Value<String?>? name,
    Value<String>? dateFrom,
    Value<String>? dateTo,
    Value<int>? rowid,
  }) {
    return CachedModulesCompanion(
      scope: scope ?? this.scope,
      moduleId: moduleId ?? this.moduleId,
      name: name ?? this.name,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (scope.present) {
      map['scope'] = Variable<String>(scope.value);
    }
    if (moduleId.present) {
      map['module_id'] = Variable<int>(moduleId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (dateFrom.present) {
      map['date_from'] = Variable<String>(dateFrom.value);
    }
    if (dateTo.present) {
      map['date_to'] = Variable<String>(dateTo.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedModulesCompanion(')
          ..write('scope: $scope, ')
          ..write('moduleId: $moduleId, ')
          ..write('name: $name, ')
          ..write('dateFrom: $dateFrom, ')
          ..write('dateTo: $dateTo, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $CachedWeekCalendarTable extends CachedWeekCalendar
    with TableInfo<$CachedWeekCalendarTable, CachedWeekCalendarData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedWeekCalendarTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _scopeMeta = const VerificationMeta('scope');
  @override
  late final GeneratedColumn<String> scope = GeneratedColumn<String>(
    'scope',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dateFromMeta = const VerificationMeta(
    'dateFrom',
  );
  @override
  late final GeneratedColumn<String> dateFrom = GeneratedColumn<String>(
    'date_from',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dateToMeta = const VerificationMeta('dateTo');
  @override
  late final GeneratedColumn<String> dateTo = GeneratedColumn<String>(
    'date_to',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
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
  @override
  List<GeneratedColumn> get $columns => [scope, dateFrom, dateTo, weekType];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_week_calendar';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedWeekCalendarData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('scope')) {
      context.handle(
        _scopeMeta,
        scope.isAcceptableOrUnknown(data['scope']!, _scopeMeta),
      );
    } else if (isInserting) {
      context.missing(_scopeMeta);
    }
    if (data.containsKey('date_from')) {
      context.handle(
        _dateFromMeta,
        dateFrom.isAcceptableOrUnknown(data['date_from']!, _dateFromMeta),
      );
    } else if (isInserting) {
      context.missing(_dateFromMeta);
    }
    if (data.containsKey('date_to')) {
      context.handle(
        _dateToMeta,
        dateTo.isAcceptableOrUnknown(data['date_to']!, _dateToMeta),
      );
    } else if (isInserting) {
      context.missing(_dateToMeta);
    }
    if (data.containsKey('week_type')) {
      context.handle(
        _weekTypeMeta,
        weekType.isAcceptableOrUnknown(data['week_type']!, _weekTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_weekTypeMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => const {};
  @override
  CachedWeekCalendarData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedWeekCalendarData(
      scope: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}scope'],
      )!,
      dateFrom: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}date_from'],
      )!,
      dateTo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}date_to'],
      )!,
      weekType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}week_type'],
      )!,
    );
  }

  @override
  $CachedWeekCalendarTable createAlias(String alias) {
    return $CachedWeekCalendarTable(attachedDatabase, alias);
  }
}

class CachedWeekCalendarData extends DataClass
    implements Insertable<CachedWeekCalendarData> {
  final String scope;
  final String dateFrom;
  final String dateTo;
  final String weekType;
  const CachedWeekCalendarData({
    required this.scope,
    required this.dateFrom,
    required this.dateTo,
    required this.weekType,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['scope'] = Variable<String>(scope);
    map['date_from'] = Variable<String>(dateFrom);
    map['date_to'] = Variable<String>(dateTo);
    map['week_type'] = Variable<String>(weekType);
    return map;
  }

  CachedWeekCalendarCompanion toCompanion(bool nullToAbsent) {
    return CachedWeekCalendarCompanion(
      scope: Value(scope),
      dateFrom: Value(dateFrom),
      dateTo: Value(dateTo),
      weekType: Value(weekType),
    );
  }

  factory CachedWeekCalendarData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedWeekCalendarData(
      scope: serializer.fromJson<String>(json['scope']),
      dateFrom: serializer.fromJson<String>(json['dateFrom']),
      dateTo: serializer.fromJson<String>(json['dateTo']),
      weekType: serializer.fromJson<String>(json['weekType']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'scope': serializer.toJson<String>(scope),
      'dateFrom': serializer.toJson<String>(dateFrom),
      'dateTo': serializer.toJson<String>(dateTo),
      'weekType': serializer.toJson<String>(weekType),
    };
  }

  CachedWeekCalendarData copyWith({
    String? scope,
    String? dateFrom,
    String? dateTo,
    String? weekType,
  }) => CachedWeekCalendarData(
    scope: scope ?? this.scope,
    dateFrom: dateFrom ?? this.dateFrom,
    dateTo: dateTo ?? this.dateTo,
    weekType: weekType ?? this.weekType,
  );
  CachedWeekCalendarData copyWithCompanion(CachedWeekCalendarCompanion data) {
    return CachedWeekCalendarData(
      scope: data.scope.present ? data.scope.value : this.scope,
      dateFrom: data.dateFrom.present ? data.dateFrom.value : this.dateFrom,
      dateTo: data.dateTo.present ? data.dateTo.value : this.dateTo,
      weekType: data.weekType.present ? data.weekType.value : this.weekType,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedWeekCalendarData(')
          ..write('scope: $scope, ')
          ..write('dateFrom: $dateFrom, ')
          ..write('dateTo: $dateTo, ')
          ..write('weekType: $weekType')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(scope, dateFrom, dateTo, weekType);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedWeekCalendarData &&
          other.scope == this.scope &&
          other.dateFrom == this.dateFrom &&
          other.dateTo == this.dateTo &&
          other.weekType == this.weekType);
}

class CachedWeekCalendarCompanion
    extends UpdateCompanion<CachedWeekCalendarData> {
  final Value<String> scope;
  final Value<String> dateFrom;
  final Value<String> dateTo;
  final Value<String> weekType;
  final Value<int> rowid;
  const CachedWeekCalendarCompanion({
    this.scope = const Value.absent(),
    this.dateFrom = const Value.absent(),
    this.dateTo = const Value.absent(),
    this.weekType = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedWeekCalendarCompanion.insert({
    required String scope,
    required String dateFrom,
    required String dateTo,
    required String weekType,
    this.rowid = const Value.absent(),
  }) : scope = Value(scope),
       dateFrom = Value(dateFrom),
       dateTo = Value(dateTo),
       weekType = Value(weekType);
  static Insertable<CachedWeekCalendarData> custom({
    Expression<String>? scope,
    Expression<String>? dateFrom,
    Expression<String>? dateTo,
    Expression<String>? weekType,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (scope != null) 'scope': scope,
      if (dateFrom != null) 'date_from': dateFrom,
      if (dateTo != null) 'date_to': dateTo,
      if (weekType != null) 'week_type': weekType,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedWeekCalendarCompanion copyWith({
    Value<String>? scope,
    Value<String>? dateFrom,
    Value<String>? dateTo,
    Value<String>? weekType,
    Value<int>? rowid,
  }) {
    return CachedWeekCalendarCompanion(
      scope: scope ?? this.scope,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
      weekType: weekType ?? this.weekType,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (scope.present) {
      map['scope'] = Variable<String>(scope.value);
    }
    if (dateFrom.present) {
      map['date_from'] = Variable<String>(dateFrom.value);
    }
    if (dateTo.present) {
      map['date_to'] = Variable<String>(dateTo.value);
    }
    if (weekType.present) {
      map['week_type'] = Variable<String>(weekType.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedWeekCalendarCompanion(')
          ..write('scope: $scope, ')
          ..write('dateFrom: $dateFrom, ')
          ..write('dateTo: $dateTo, ')
          ..write('weekType: $weekType, ')
          ..write('rowid: $rowid')
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
  static const VerificationMeta _scopeMeta = const VerificationMeta('scope');
  @override
  late final GeneratedColumn<String> scope = GeneratedColumn<String>(
    'scope',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
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
  List<GeneratedColumn> get $columns => [scope, etag, syncedAt];
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
    if (data.containsKey('scope')) {
      context.handle(
        _scopeMeta,
        scope.isAcceptableOrUnknown(data['scope']!, _scopeMeta),
      );
    } else if (isInserting) {
      context.missing(_scopeMeta);
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
  Set<GeneratedColumn> get $primaryKey => {scope};
  @override
  ScheduleCacheMetaData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ScheduleCacheMetaData(
      scope: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}scope'],
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
  final String scope;
  final String? etag;
  final DateTime syncedAt;
  const ScheduleCacheMetaData({
    required this.scope,
    this.etag,
    required this.syncedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['scope'] = Variable<String>(scope);
    if (!nullToAbsent || etag != null) {
      map['etag'] = Variable<String>(etag);
    }
    map['synced_at'] = Variable<DateTime>(syncedAt);
    return map;
  }

  ScheduleCacheMetaCompanion toCompanion(bool nullToAbsent) {
    return ScheduleCacheMetaCompanion(
      scope: Value(scope),
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
      scope: serializer.fromJson<String>(json['scope']),
      etag: serializer.fromJson<String?>(json['etag']),
      syncedAt: serializer.fromJson<DateTime>(json['syncedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'scope': serializer.toJson<String>(scope),
      'etag': serializer.toJson<String?>(etag),
      'syncedAt': serializer.toJson<DateTime>(syncedAt),
    };
  }

  ScheduleCacheMetaData copyWith({
    String? scope,
    Value<String?> etag = const Value.absent(),
    DateTime? syncedAt,
  }) => ScheduleCacheMetaData(
    scope: scope ?? this.scope,
    etag: etag.present ? etag.value : this.etag,
    syncedAt: syncedAt ?? this.syncedAt,
  );
  ScheduleCacheMetaData copyWithCompanion(ScheduleCacheMetaCompanion data) {
    return ScheduleCacheMetaData(
      scope: data.scope.present ? data.scope.value : this.scope,
      etag: data.etag.present ? data.etag.value : this.etag,
      syncedAt: data.syncedAt.present ? data.syncedAt.value : this.syncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ScheduleCacheMetaData(')
          ..write('scope: $scope, ')
          ..write('etag: $etag, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(scope, etag, syncedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ScheduleCacheMetaData &&
          other.scope == this.scope &&
          other.etag == this.etag &&
          other.syncedAt == this.syncedAt);
}

class ScheduleCacheMetaCompanion
    extends UpdateCompanion<ScheduleCacheMetaData> {
  final Value<String> scope;
  final Value<String?> etag;
  final Value<DateTime> syncedAt;
  final Value<int> rowid;
  const ScheduleCacheMetaCompanion({
    this.scope = const Value.absent(),
    this.etag = const Value.absent(),
    this.syncedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ScheduleCacheMetaCompanion.insert({
    required String scope,
    this.etag = const Value.absent(),
    required DateTime syncedAt,
    this.rowid = const Value.absent(),
  }) : scope = Value(scope),
       syncedAt = Value(syncedAt);
  static Insertable<ScheduleCacheMetaData> custom({
    Expression<String>? scope,
    Expression<String>? etag,
    Expression<DateTime>? syncedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (scope != null) 'scope': scope,
      if (etag != null) 'etag': etag,
      if (syncedAt != null) 'synced_at': syncedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ScheduleCacheMetaCompanion copyWith({
    Value<String>? scope,
    Value<String?>? etag,
    Value<DateTime>? syncedAt,
    Value<int>? rowid,
  }) {
    return ScheduleCacheMetaCompanion(
      scope: scope ?? this.scope,
      etag: etag ?? this.etag,
      syncedAt: syncedAt ?? this.syncedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (scope.present) {
      map['scope'] = Variable<String>(scope.value);
    }
    if (etag.present) {
      map['etag'] = Variable<String>(etag.value);
    }
    if (syncedAt.present) {
      map['synced_at'] = Variable<DateTime>(syncedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ScheduleCacheMetaCompanion(')
          ..write('scope: $scope, ')
          ..write('etag: $etag, ')
          ..write('syncedAt: $syncedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $CachedExamsTable extends CachedExams
    with TableInfo<$CachedExamsTable, CachedExam> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedExamsTable(this.attachedDatabase, [this._alias]);
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
  static const VerificationMeta _teacherMeta = const VerificationMeta(
    'teacher',
  );
  @override
  late final GeneratedColumn<String> teacher = GeneratedColumn<String>(
    'teacher',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _consultationAtMeta = const VerificationMeta(
    'consultationAt',
  );
  @override
  late final GeneratedColumn<String> consultationAt = GeneratedColumn<String>(
    'consultation_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _examAtMeta = const VerificationMeta('examAt');
  @override
  late final GeneratedColumn<String> examAt = GeneratedColumn<String>(
    'exam_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
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
  static const VerificationMeta _kindMeta = const VerificationMeta('kind');
  @override
  late final GeneratedColumn<String> kind = GeneratedColumn<String>(
    'kind',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    groupId,
    subject,
    teacher,
    consultationAt,
    examAt,
    room,
    kind,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_exams';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedExam> instance, {
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
    if (data.containsKey('subject')) {
      context.handle(
        _subjectMeta,
        subject.isAcceptableOrUnknown(data['subject']!, _subjectMeta),
      );
    } else if (isInserting) {
      context.missing(_subjectMeta);
    }
    if (data.containsKey('teacher')) {
      context.handle(
        _teacherMeta,
        teacher.isAcceptableOrUnknown(data['teacher']!, _teacherMeta),
      );
    }
    if (data.containsKey('consultation_at')) {
      context.handle(
        _consultationAtMeta,
        consultationAt.isAcceptableOrUnknown(
          data['consultation_at']!,
          _consultationAtMeta,
        ),
      );
    }
    if (data.containsKey('exam_at')) {
      context.handle(
        _examAtMeta,
        examAt.isAcceptableOrUnknown(data['exam_at']!, _examAtMeta),
      );
    }
    if (data.containsKey('room')) {
      context.handle(
        _roomMeta,
        room.isAcceptableOrUnknown(data['room']!, _roomMeta),
      );
    }
    if (data.containsKey('kind')) {
      context.handle(
        _kindMeta,
        kind.isAcceptableOrUnknown(data['kind']!, _kindMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedExam map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedExam(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      groupId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}group_id'],
      )!,
      subject: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}subject'],
      )!,
      teacher: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}teacher'],
      ),
      consultationAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}consultation_at'],
      ),
      examAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}exam_at'],
      ),
      room: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}room'],
      ),
      kind: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}kind'],
      ),
    );
  }

  @override
  $CachedExamsTable createAlias(String alias) {
    return $CachedExamsTable(attachedDatabase, alias);
  }
}

class CachedExam extends DataClass implements Insertable<CachedExam> {
  final int id;
  final int groupId;
  final String subject;
  final String? teacher;
  final String? consultationAt;
  final String? examAt;
  final String? room;
  final String? kind;
  const CachedExam({
    required this.id,
    required this.groupId,
    required this.subject,
    this.teacher,
    this.consultationAt,
    this.examAt,
    this.room,
    this.kind,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['group_id'] = Variable<int>(groupId);
    map['subject'] = Variable<String>(subject);
    if (!nullToAbsent || teacher != null) {
      map['teacher'] = Variable<String>(teacher);
    }
    if (!nullToAbsent || consultationAt != null) {
      map['consultation_at'] = Variable<String>(consultationAt);
    }
    if (!nullToAbsent || examAt != null) {
      map['exam_at'] = Variable<String>(examAt);
    }
    if (!nullToAbsent || room != null) {
      map['room'] = Variable<String>(room);
    }
    if (!nullToAbsent || kind != null) {
      map['kind'] = Variable<String>(kind);
    }
    return map;
  }

  CachedExamsCompanion toCompanion(bool nullToAbsent) {
    return CachedExamsCompanion(
      id: Value(id),
      groupId: Value(groupId),
      subject: Value(subject),
      teacher: teacher == null && nullToAbsent
          ? const Value.absent()
          : Value(teacher),
      consultationAt: consultationAt == null && nullToAbsent
          ? const Value.absent()
          : Value(consultationAt),
      examAt: examAt == null && nullToAbsent
          ? const Value.absent()
          : Value(examAt),
      room: room == null && nullToAbsent ? const Value.absent() : Value(room),
      kind: kind == null && nullToAbsent ? const Value.absent() : Value(kind),
    );
  }

  factory CachedExam.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedExam(
      id: serializer.fromJson<int>(json['id']),
      groupId: serializer.fromJson<int>(json['groupId']),
      subject: serializer.fromJson<String>(json['subject']),
      teacher: serializer.fromJson<String?>(json['teacher']),
      consultationAt: serializer.fromJson<String?>(json['consultationAt']),
      examAt: serializer.fromJson<String?>(json['examAt']),
      room: serializer.fromJson<String?>(json['room']),
      kind: serializer.fromJson<String?>(json['kind']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'groupId': serializer.toJson<int>(groupId),
      'subject': serializer.toJson<String>(subject),
      'teacher': serializer.toJson<String?>(teacher),
      'consultationAt': serializer.toJson<String?>(consultationAt),
      'examAt': serializer.toJson<String?>(examAt),
      'room': serializer.toJson<String?>(room),
      'kind': serializer.toJson<String?>(kind),
    };
  }

  CachedExam copyWith({
    int? id,
    int? groupId,
    String? subject,
    Value<String?> teacher = const Value.absent(),
    Value<String?> consultationAt = const Value.absent(),
    Value<String?> examAt = const Value.absent(),
    Value<String?> room = const Value.absent(),
    Value<String?> kind = const Value.absent(),
  }) => CachedExam(
    id: id ?? this.id,
    groupId: groupId ?? this.groupId,
    subject: subject ?? this.subject,
    teacher: teacher.present ? teacher.value : this.teacher,
    consultationAt: consultationAt.present
        ? consultationAt.value
        : this.consultationAt,
    examAt: examAt.present ? examAt.value : this.examAt,
    room: room.present ? room.value : this.room,
    kind: kind.present ? kind.value : this.kind,
  );
  CachedExam copyWithCompanion(CachedExamsCompanion data) {
    return CachedExam(
      id: data.id.present ? data.id.value : this.id,
      groupId: data.groupId.present ? data.groupId.value : this.groupId,
      subject: data.subject.present ? data.subject.value : this.subject,
      teacher: data.teacher.present ? data.teacher.value : this.teacher,
      consultationAt: data.consultationAt.present
          ? data.consultationAt.value
          : this.consultationAt,
      examAt: data.examAt.present ? data.examAt.value : this.examAt,
      room: data.room.present ? data.room.value : this.room,
      kind: data.kind.present ? data.kind.value : this.kind,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedExam(')
          ..write('id: $id, ')
          ..write('groupId: $groupId, ')
          ..write('subject: $subject, ')
          ..write('teacher: $teacher, ')
          ..write('consultationAt: $consultationAt, ')
          ..write('examAt: $examAt, ')
          ..write('room: $room, ')
          ..write('kind: $kind')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    groupId,
    subject,
    teacher,
    consultationAt,
    examAt,
    room,
    kind,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedExam &&
          other.id == this.id &&
          other.groupId == this.groupId &&
          other.subject == this.subject &&
          other.teacher == this.teacher &&
          other.consultationAt == this.consultationAt &&
          other.examAt == this.examAt &&
          other.room == this.room &&
          other.kind == this.kind);
}

class CachedExamsCompanion extends UpdateCompanion<CachedExam> {
  final Value<int> id;
  final Value<int> groupId;
  final Value<String> subject;
  final Value<String?> teacher;
  final Value<String?> consultationAt;
  final Value<String?> examAt;
  final Value<String?> room;
  final Value<String?> kind;
  const CachedExamsCompanion({
    this.id = const Value.absent(),
    this.groupId = const Value.absent(),
    this.subject = const Value.absent(),
    this.teacher = const Value.absent(),
    this.consultationAt = const Value.absent(),
    this.examAt = const Value.absent(),
    this.room = const Value.absent(),
    this.kind = const Value.absent(),
  });
  CachedExamsCompanion.insert({
    this.id = const Value.absent(),
    required int groupId,
    required String subject,
    this.teacher = const Value.absent(),
    this.consultationAt = const Value.absent(),
    this.examAt = const Value.absent(),
    this.room = const Value.absent(),
    this.kind = const Value.absent(),
  }) : groupId = Value(groupId),
       subject = Value(subject);
  static Insertable<CachedExam> custom({
    Expression<int>? id,
    Expression<int>? groupId,
    Expression<String>? subject,
    Expression<String>? teacher,
    Expression<String>? consultationAt,
    Expression<String>? examAt,
    Expression<String>? room,
    Expression<String>? kind,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (groupId != null) 'group_id': groupId,
      if (subject != null) 'subject': subject,
      if (teacher != null) 'teacher': teacher,
      if (consultationAt != null) 'consultation_at': consultationAt,
      if (examAt != null) 'exam_at': examAt,
      if (room != null) 'room': room,
      if (kind != null) 'kind': kind,
    });
  }

  CachedExamsCompanion copyWith({
    Value<int>? id,
    Value<int>? groupId,
    Value<String>? subject,
    Value<String?>? teacher,
    Value<String?>? consultationAt,
    Value<String?>? examAt,
    Value<String?>? room,
    Value<String?>? kind,
  }) {
    return CachedExamsCompanion(
      id: id ?? this.id,
      groupId: groupId ?? this.groupId,
      subject: subject ?? this.subject,
      teacher: teacher ?? this.teacher,
      consultationAt: consultationAt ?? this.consultationAt,
      examAt: examAt ?? this.examAt,
      room: room ?? this.room,
      kind: kind ?? this.kind,
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
    if (subject.present) {
      map['subject'] = Variable<String>(subject.value);
    }
    if (teacher.present) {
      map['teacher'] = Variable<String>(teacher.value);
    }
    if (consultationAt.present) {
      map['consultation_at'] = Variable<String>(consultationAt.value);
    }
    if (examAt.present) {
      map['exam_at'] = Variable<String>(examAt.value);
    }
    if (room.present) {
      map['room'] = Variable<String>(room.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>(kind.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedExamsCompanion(')
          ..write('id: $id, ')
          ..write('groupId: $groupId, ')
          ..write('subject: $subject, ')
          ..write('teacher: $teacher, ')
          ..write('consultationAt: $consultationAt, ')
          ..write('examAt: $examAt, ')
          ..write('room: $room, ')
          ..write('kind: $kind')
          ..write(')'))
        .toString();
  }
}

class $ExamCacheMetaTable extends ExamCacheMeta
    with TableInfo<$ExamCacheMetaTable, ExamCacheMetaData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ExamCacheMetaTable(this.attachedDatabase, [this._alias]);
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
  static const String $name = 'exam_cache_meta';
  @override
  VerificationContext validateIntegrity(
    Insertable<ExamCacheMetaData> instance, {
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
  ExamCacheMetaData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ExamCacheMetaData(
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
  $ExamCacheMetaTable createAlias(String alias) {
    return $ExamCacheMetaTable(attachedDatabase, alias);
  }
}

class ExamCacheMetaData extends DataClass
    implements Insertable<ExamCacheMetaData> {
  final int groupId;
  final String? etag;
  final DateTime syncedAt;
  const ExamCacheMetaData({
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

  ExamCacheMetaCompanion toCompanion(bool nullToAbsent) {
    return ExamCacheMetaCompanion(
      groupId: Value(groupId),
      etag: etag == null && nullToAbsent ? const Value.absent() : Value(etag),
      syncedAt: Value(syncedAt),
    );
  }

  factory ExamCacheMetaData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ExamCacheMetaData(
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

  ExamCacheMetaData copyWith({
    int? groupId,
    Value<String?> etag = const Value.absent(),
    DateTime? syncedAt,
  }) => ExamCacheMetaData(
    groupId: groupId ?? this.groupId,
    etag: etag.present ? etag.value : this.etag,
    syncedAt: syncedAt ?? this.syncedAt,
  );
  ExamCacheMetaData copyWithCompanion(ExamCacheMetaCompanion data) {
    return ExamCacheMetaData(
      groupId: data.groupId.present ? data.groupId.value : this.groupId,
      etag: data.etag.present ? data.etag.value : this.etag,
      syncedAt: data.syncedAt.present ? data.syncedAt.value : this.syncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ExamCacheMetaData(')
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
      (other is ExamCacheMetaData &&
          other.groupId == this.groupId &&
          other.etag == this.etag &&
          other.syncedAt == this.syncedAt);
}

class ExamCacheMetaCompanion extends UpdateCompanion<ExamCacheMetaData> {
  final Value<int> groupId;
  final Value<String?> etag;
  final Value<DateTime> syncedAt;
  const ExamCacheMetaCompanion({
    this.groupId = const Value.absent(),
    this.etag = const Value.absent(),
    this.syncedAt = const Value.absent(),
  });
  ExamCacheMetaCompanion.insert({
    this.groupId = const Value.absent(),
    this.etag = const Value.absent(),
    required DateTime syncedAt,
  }) : syncedAt = Value(syncedAt);
  static Insertable<ExamCacheMetaData> custom({
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

  ExamCacheMetaCompanion copyWith({
    Value<int>? groupId,
    Value<String?>? etag,
    Value<DateTime>? syncedAt,
  }) {
    return ExamCacheMetaCompanion(
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
    return (StringBuffer('ExamCacheMetaCompanion(')
          ..write('groupId: $groupId, ')
          ..write('etag: $etag, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }
}

class $CachedNewsTable extends CachedNews
    with TableInfo<$CachedNewsTable, CachedNew> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedNewsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _bodyMeta = const VerificationMeta('body');
  @override
  late final GeneratedColumn<String> body = GeneratedColumn<String>(
    'body',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sourceMeta = const VerificationMeta('source');
  @override
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
    'source',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _urlMeta = const VerificationMeta('url');
  @override
  late final GeneratedColumn<String> url = GeneratedColumn<String>(
    'url',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _imageUrlMeta = const VerificationMeta(
    'imageUrl',
  );
  @override
  late final GeneratedColumn<String> imageUrl = GeneratedColumn<String>(
    'image_url',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _isImportantMeta = const VerificationMeta(
    'isImportant',
  );
  @override
  late final GeneratedColumn<bool> isImportant = GeneratedColumn<bool>(
    'is_important',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_important" IN (0, 1))',
    ),
  );
  static const VerificationMeta _publishedAtMeta = const VerificationMeta(
    'publishedAt',
  );
  @override
  late final GeneratedColumn<DateTime> publishedAt = GeneratedColumn<DateTime>(
    'published_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    title,
    body,
    source,
    url,
    imageUrl,
    isImportant,
    publishedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_news';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedNew> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('body')) {
      context.handle(
        _bodyMeta,
        body.isAcceptableOrUnknown(data['body']!, _bodyMeta),
      );
    } else if (isInserting) {
      context.missing(_bodyMeta);
    }
    if (data.containsKey('source')) {
      context.handle(
        _sourceMeta,
        source.isAcceptableOrUnknown(data['source']!, _sourceMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceMeta);
    }
    if (data.containsKey('url')) {
      context.handle(
        _urlMeta,
        url.isAcceptableOrUnknown(data['url']!, _urlMeta),
      );
    } else if (isInserting) {
      context.missing(_urlMeta);
    }
    if (data.containsKey('image_url')) {
      context.handle(
        _imageUrlMeta,
        imageUrl.isAcceptableOrUnknown(data['image_url']!, _imageUrlMeta),
      );
    }
    if (data.containsKey('is_important')) {
      context.handle(
        _isImportantMeta,
        isImportant.isAcceptableOrUnknown(
          data['is_important']!,
          _isImportantMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_isImportantMeta);
    }
    if (data.containsKey('published_at')) {
      context.handle(
        _publishedAtMeta,
        publishedAt.isAcceptableOrUnknown(
          data['published_at']!,
          _publishedAtMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_publishedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedNew map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedNew(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      body: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}body'],
      )!,
      source: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source'],
      )!,
      url: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}url'],
      )!,
      imageUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}image_url'],
      ),
      isImportant: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_important'],
      )!,
      publishedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}published_at'],
      )!,
    );
  }

  @override
  $CachedNewsTable createAlias(String alias) {
    return $CachedNewsTable(attachedDatabase, alias);
  }
}

class CachedNew extends DataClass implements Insertable<CachedNew> {
  final int id;
  final String title;
  final String body;
  final String source;
  final String url;
  final String? imageUrl;
  final bool isImportant;
  final DateTime publishedAt;
  const CachedNew({
    required this.id,
    required this.title,
    required this.body,
    required this.source,
    required this.url,
    this.imageUrl,
    required this.isImportant,
    required this.publishedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['title'] = Variable<String>(title);
    map['body'] = Variable<String>(body);
    map['source'] = Variable<String>(source);
    map['url'] = Variable<String>(url);
    if (!nullToAbsent || imageUrl != null) {
      map['image_url'] = Variable<String>(imageUrl);
    }
    map['is_important'] = Variable<bool>(isImportant);
    map['published_at'] = Variable<DateTime>(publishedAt);
    return map;
  }

  CachedNewsCompanion toCompanion(bool nullToAbsent) {
    return CachedNewsCompanion(
      id: Value(id),
      title: Value(title),
      body: Value(body),
      source: Value(source),
      url: Value(url),
      imageUrl: imageUrl == null && nullToAbsent
          ? const Value.absent()
          : Value(imageUrl),
      isImportant: Value(isImportant),
      publishedAt: Value(publishedAt),
    );
  }

  factory CachedNew.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedNew(
      id: serializer.fromJson<int>(json['id']),
      title: serializer.fromJson<String>(json['title']),
      body: serializer.fromJson<String>(json['body']),
      source: serializer.fromJson<String>(json['source']),
      url: serializer.fromJson<String>(json['url']),
      imageUrl: serializer.fromJson<String?>(json['imageUrl']),
      isImportant: serializer.fromJson<bool>(json['isImportant']),
      publishedAt: serializer.fromJson<DateTime>(json['publishedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'title': serializer.toJson<String>(title),
      'body': serializer.toJson<String>(body),
      'source': serializer.toJson<String>(source),
      'url': serializer.toJson<String>(url),
      'imageUrl': serializer.toJson<String?>(imageUrl),
      'isImportant': serializer.toJson<bool>(isImportant),
      'publishedAt': serializer.toJson<DateTime>(publishedAt),
    };
  }

  CachedNew copyWith({
    int? id,
    String? title,
    String? body,
    String? source,
    String? url,
    Value<String?> imageUrl = const Value.absent(),
    bool? isImportant,
    DateTime? publishedAt,
  }) => CachedNew(
    id: id ?? this.id,
    title: title ?? this.title,
    body: body ?? this.body,
    source: source ?? this.source,
    url: url ?? this.url,
    imageUrl: imageUrl.present ? imageUrl.value : this.imageUrl,
    isImportant: isImportant ?? this.isImportant,
    publishedAt: publishedAt ?? this.publishedAt,
  );
  CachedNew copyWithCompanion(CachedNewsCompanion data) {
    return CachedNew(
      id: data.id.present ? data.id.value : this.id,
      title: data.title.present ? data.title.value : this.title,
      body: data.body.present ? data.body.value : this.body,
      source: data.source.present ? data.source.value : this.source,
      url: data.url.present ? data.url.value : this.url,
      imageUrl: data.imageUrl.present ? data.imageUrl.value : this.imageUrl,
      isImportant: data.isImportant.present
          ? data.isImportant.value
          : this.isImportant,
      publishedAt: data.publishedAt.present
          ? data.publishedAt.value
          : this.publishedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedNew(')
          ..write('id: $id, ')
          ..write('title: $title, ')
          ..write('body: $body, ')
          ..write('source: $source, ')
          ..write('url: $url, ')
          ..write('imageUrl: $imageUrl, ')
          ..write('isImportant: $isImportant, ')
          ..write('publishedAt: $publishedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    title,
    body,
    source,
    url,
    imageUrl,
    isImportant,
    publishedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedNew &&
          other.id == this.id &&
          other.title == this.title &&
          other.body == this.body &&
          other.source == this.source &&
          other.url == this.url &&
          other.imageUrl == this.imageUrl &&
          other.isImportant == this.isImportant &&
          other.publishedAt == this.publishedAt);
}

class CachedNewsCompanion extends UpdateCompanion<CachedNew> {
  final Value<int> id;
  final Value<String> title;
  final Value<String> body;
  final Value<String> source;
  final Value<String> url;
  final Value<String?> imageUrl;
  final Value<bool> isImportant;
  final Value<DateTime> publishedAt;
  const CachedNewsCompanion({
    this.id = const Value.absent(),
    this.title = const Value.absent(),
    this.body = const Value.absent(),
    this.source = const Value.absent(),
    this.url = const Value.absent(),
    this.imageUrl = const Value.absent(),
    this.isImportant = const Value.absent(),
    this.publishedAt = const Value.absent(),
  });
  CachedNewsCompanion.insert({
    this.id = const Value.absent(),
    required String title,
    required String body,
    required String source,
    required String url,
    this.imageUrl = const Value.absent(),
    required bool isImportant,
    required DateTime publishedAt,
  }) : title = Value(title),
       body = Value(body),
       source = Value(source),
       url = Value(url),
       isImportant = Value(isImportant),
       publishedAt = Value(publishedAt);
  static Insertable<CachedNew> custom({
    Expression<int>? id,
    Expression<String>? title,
    Expression<String>? body,
    Expression<String>? source,
    Expression<String>? url,
    Expression<String>? imageUrl,
    Expression<bool>? isImportant,
    Expression<DateTime>? publishedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (title != null) 'title': title,
      if (body != null) 'body': body,
      if (source != null) 'source': source,
      if (url != null) 'url': url,
      if (imageUrl != null) 'image_url': imageUrl,
      if (isImportant != null) 'is_important': isImportant,
      if (publishedAt != null) 'published_at': publishedAt,
    });
  }

  CachedNewsCompanion copyWith({
    Value<int>? id,
    Value<String>? title,
    Value<String>? body,
    Value<String>? source,
    Value<String>? url,
    Value<String?>? imageUrl,
    Value<bool>? isImportant,
    Value<DateTime>? publishedAt,
  }) {
    return CachedNewsCompanion(
      id: id ?? this.id,
      title: title ?? this.title,
      body: body ?? this.body,
      source: source ?? this.source,
      url: url ?? this.url,
      imageUrl: imageUrl ?? this.imageUrl,
      isImportant: isImportant ?? this.isImportant,
      publishedAt: publishedAt ?? this.publishedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (body.present) {
      map['body'] = Variable<String>(body.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    if (url.present) {
      map['url'] = Variable<String>(url.value);
    }
    if (imageUrl.present) {
      map['image_url'] = Variable<String>(imageUrl.value);
    }
    if (isImportant.present) {
      map['is_important'] = Variable<bool>(isImportant.value);
    }
    if (publishedAt.present) {
      map['published_at'] = Variable<DateTime>(publishedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedNewsCompanion(')
          ..write('id: $id, ')
          ..write('title: $title, ')
          ..write('body: $body, ')
          ..write('source: $source, ')
          ..write('url: $url, ')
          ..write('imageUrl: $imageUrl, ')
          ..write('isImportant: $isImportant, ')
          ..write('publishedAt: $publishedAt')
          ..write(')'))
        .toString();
  }
}

class $CachedContactsTable extends CachedContacts
    with TableInfo<$CachedContactsTable, CachedContact> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedContactsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sectionMeta = const VerificationMeta(
    'section',
  );
  @override
  late final GeneratedColumn<String> section = GeneratedColumn<String>(
    'section',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _roleMeta = const VerificationMeta('role');
  @override
  late final GeneratedColumn<String> role = GeneratedColumn<String>(
    'role',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _officeMeta = const VerificationMeta('office');
  @override
  late final GeneratedColumn<String> office = GeneratedColumn<String>(
    'office',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _emailMeta = const VerificationMeta('email');
  @override
  late final GeneratedColumn<String> email = GeneratedColumn<String>(
    'email',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _phoneMeta = const VerificationMeta('phone');
  @override
  late final GeneratedColumn<String> phone = GeneratedColumn<String>(
    'phone',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _officeHoursMeta = const VerificationMeta(
    'officeHours',
  );
  @override
  late final GeneratedColumn<String> officeHours = GeneratedColumn<String>(
    'office_hours',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    section,
    name,
    role,
    office,
    email,
    phone,
    officeHours,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_contacts';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedContact> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('section')) {
      context.handle(
        _sectionMeta,
        section.isAcceptableOrUnknown(data['section']!, _sectionMeta),
      );
    } else if (isInserting) {
      context.missing(_sectionMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('role')) {
      context.handle(
        _roleMeta,
        role.isAcceptableOrUnknown(data['role']!, _roleMeta),
      );
    }
    if (data.containsKey('office')) {
      context.handle(
        _officeMeta,
        office.isAcceptableOrUnknown(data['office']!, _officeMeta),
      );
    }
    if (data.containsKey('email')) {
      context.handle(
        _emailMeta,
        email.isAcceptableOrUnknown(data['email']!, _emailMeta),
      );
    }
    if (data.containsKey('phone')) {
      context.handle(
        _phoneMeta,
        phone.isAcceptableOrUnknown(data['phone']!, _phoneMeta),
      );
    }
    if (data.containsKey('office_hours')) {
      context.handle(
        _officeHoursMeta,
        officeHours.isAcceptableOrUnknown(
          data['office_hours']!,
          _officeHoursMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedContact map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedContact(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      section: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}section'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      role: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}role'],
      ),
      office: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}office'],
      ),
      email: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}email'],
      ),
      phone: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}phone'],
      ),
      officeHours: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}office_hours'],
      ),
    );
  }

  @override
  $CachedContactsTable createAlias(String alias) {
    return $CachedContactsTable(attachedDatabase, alias);
  }
}

class CachedContact extends DataClass implements Insertable<CachedContact> {
  final int id;
  final String section;
  final String name;
  final String? role;
  final String? office;
  final String? email;
  final String? phone;
  final String? officeHours;
  const CachedContact({
    required this.id,
    required this.section,
    required this.name,
    this.role,
    this.office,
    this.email,
    this.phone,
    this.officeHours,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['section'] = Variable<String>(section);
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || role != null) {
      map['role'] = Variable<String>(role);
    }
    if (!nullToAbsent || office != null) {
      map['office'] = Variable<String>(office);
    }
    if (!nullToAbsent || email != null) {
      map['email'] = Variable<String>(email);
    }
    if (!nullToAbsent || phone != null) {
      map['phone'] = Variable<String>(phone);
    }
    if (!nullToAbsent || officeHours != null) {
      map['office_hours'] = Variable<String>(officeHours);
    }
    return map;
  }

  CachedContactsCompanion toCompanion(bool nullToAbsent) {
    return CachedContactsCompanion(
      id: Value(id),
      section: Value(section),
      name: Value(name),
      role: role == null && nullToAbsent ? const Value.absent() : Value(role),
      office: office == null && nullToAbsent
          ? const Value.absent()
          : Value(office),
      email: email == null && nullToAbsent
          ? const Value.absent()
          : Value(email),
      phone: phone == null && nullToAbsent
          ? const Value.absent()
          : Value(phone),
      officeHours: officeHours == null && nullToAbsent
          ? const Value.absent()
          : Value(officeHours),
    );
  }

  factory CachedContact.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedContact(
      id: serializer.fromJson<int>(json['id']),
      section: serializer.fromJson<String>(json['section']),
      name: serializer.fromJson<String>(json['name']),
      role: serializer.fromJson<String?>(json['role']),
      office: serializer.fromJson<String?>(json['office']),
      email: serializer.fromJson<String?>(json['email']),
      phone: serializer.fromJson<String?>(json['phone']),
      officeHours: serializer.fromJson<String?>(json['officeHours']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'section': serializer.toJson<String>(section),
      'name': serializer.toJson<String>(name),
      'role': serializer.toJson<String?>(role),
      'office': serializer.toJson<String?>(office),
      'email': serializer.toJson<String?>(email),
      'phone': serializer.toJson<String?>(phone),
      'officeHours': serializer.toJson<String?>(officeHours),
    };
  }

  CachedContact copyWith({
    int? id,
    String? section,
    String? name,
    Value<String?> role = const Value.absent(),
    Value<String?> office = const Value.absent(),
    Value<String?> email = const Value.absent(),
    Value<String?> phone = const Value.absent(),
    Value<String?> officeHours = const Value.absent(),
  }) => CachedContact(
    id: id ?? this.id,
    section: section ?? this.section,
    name: name ?? this.name,
    role: role.present ? role.value : this.role,
    office: office.present ? office.value : this.office,
    email: email.present ? email.value : this.email,
    phone: phone.present ? phone.value : this.phone,
    officeHours: officeHours.present ? officeHours.value : this.officeHours,
  );
  CachedContact copyWithCompanion(CachedContactsCompanion data) {
    return CachedContact(
      id: data.id.present ? data.id.value : this.id,
      section: data.section.present ? data.section.value : this.section,
      name: data.name.present ? data.name.value : this.name,
      role: data.role.present ? data.role.value : this.role,
      office: data.office.present ? data.office.value : this.office,
      email: data.email.present ? data.email.value : this.email,
      phone: data.phone.present ? data.phone.value : this.phone,
      officeHours: data.officeHours.present
          ? data.officeHours.value
          : this.officeHours,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedContact(')
          ..write('id: $id, ')
          ..write('section: $section, ')
          ..write('name: $name, ')
          ..write('role: $role, ')
          ..write('office: $office, ')
          ..write('email: $email, ')
          ..write('phone: $phone, ')
          ..write('officeHours: $officeHours')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, section, name, role, office, email, phone, officeHours);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedContact &&
          other.id == this.id &&
          other.section == this.section &&
          other.name == this.name &&
          other.role == this.role &&
          other.office == this.office &&
          other.email == this.email &&
          other.phone == this.phone &&
          other.officeHours == this.officeHours);
}

class CachedContactsCompanion extends UpdateCompanion<CachedContact> {
  final Value<int> id;
  final Value<String> section;
  final Value<String> name;
  final Value<String?> role;
  final Value<String?> office;
  final Value<String?> email;
  final Value<String?> phone;
  final Value<String?> officeHours;
  const CachedContactsCompanion({
    this.id = const Value.absent(),
    this.section = const Value.absent(),
    this.name = const Value.absent(),
    this.role = const Value.absent(),
    this.office = const Value.absent(),
    this.email = const Value.absent(),
    this.phone = const Value.absent(),
    this.officeHours = const Value.absent(),
  });
  CachedContactsCompanion.insert({
    this.id = const Value.absent(),
    required String section,
    required String name,
    this.role = const Value.absent(),
    this.office = const Value.absent(),
    this.email = const Value.absent(),
    this.phone = const Value.absent(),
    this.officeHours = const Value.absent(),
  }) : section = Value(section),
       name = Value(name);
  static Insertable<CachedContact> custom({
    Expression<int>? id,
    Expression<String>? section,
    Expression<String>? name,
    Expression<String>? role,
    Expression<String>? office,
    Expression<String>? email,
    Expression<String>? phone,
    Expression<String>? officeHours,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (section != null) 'section': section,
      if (name != null) 'name': name,
      if (role != null) 'role': role,
      if (office != null) 'office': office,
      if (email != null) 'email': email,
      if (phone != null) 'phone': phone,
      if (officeHours != null) 'office_hours': officeHours,
    });
  }

  CachedContactsCompanion copyWith({
    Value<int>? id,
    Value<String>? section,
    Value<String>? name,
    Value<String?>? role,
    Value<String?>? office,
    Value<String?>? email,
    Value<String?>? phone,
    Value<String?>? officeHours,
  }) {
    return CachedContactsCompanion(
      id: id ?? this.id,
      section: section ?? this.section,
      name: name ?? this.name,
      role: role ?? this.role,
      office: office ?? this.office,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      officeHours: officeHours ?? this.officeHours,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (section.present) {
      map['section'] = Variable<String>(section.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (role.present) {
      map['role'] = Variable<String>(role.value);
    }
    if (office.present) {
      map['office'] = Variable<String>(office.value);
    }
    if (email.present) {
      map['email'] = Variable<String>(email.value);
    }
    if (phone.present) {
      map['phone'] = Variable<String>(phone.value);
    }
    if (officeHours.present) {
      map['office_hours'] = Variable<String>(officeHours.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedContactsCompanion(')
          ..write('id: $id, ')
          ..write('section: $section, ')
          ..write('name: $name, ')
          ..write('role: $role, ')
          ..write('office: $office, ')
          ..write('email: $email, ')
          ..write('phone: $phone, ')
          ..write('officeHours: $officeHours')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $CachedLessonsTable cachedLessons = $CachedLessonsTable(this);
  late final $CachedModulesTable cachedModules = $CachedModulesTable(this);
  late final $CachedWeekCalendarTable cachedWeekCalendar =
      $CachedWeekCalendarTable(this);
  late final $ScheduleCacheMetaTable scheduleCacheMeta =
      $ScheduleCacheMetaTable(this);
  late final $CachedExamsTable cachedExams = $CachedExamsTable(this);
  late final $ExamCacheMetaTable examCacheMeta = $ExamCacheMetaTable(this);
  late final $CachedNewsTable cachedNews = $CachedNewsTable(this);
  late final $CachedContactsTable cachedContacts = $CachedContactsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    cachedLessons,
    cachedModules,
    cachedWeekCalendar,
    scheduleCacheMeta,
    cachedExams,
    examCacheMeta,
    cachedNews,
    cachedContacts,
  ];
}

typedef $$CachedLessonsTableCreateCompanionBuilder =
    CachedLessonsCompanion Function({
      required int id,
      required String scope,
      required int groupId,
      required int weekday,
      required int pairNumber,
      required String startsAt,
      required String endsAt,
      required String subject,
      Value<String?> room,
      Value<String?> weekType,
      required int subgroup,
      Value<String?> teacherName,
      Value<int?> moduleId,
      Value<String?> validFrom,
      Value<String?> validTo,
      Value<int> rowid,
    });
typedef $$CachedLessonsTableUpdateCompanionBuilder =
    CachedLessonsCompanion Function({
      Value<int> id,
      Value<String> scope,
      Value<int> groupId,
      Value<int> weekday,
      Value<int> pairNumber,
      Value<String> startsAt,
      Value<String> endsAt,
      Value<String> subject,
      Value<String?> room,
      Value<String?> weekType,
      Value<int> subgroup,
      Value<String?> teacherName,
      Value<int?> moduleId,
      Value<String?> validFrom,
      Value<String?> validTo,
      Value<int> rowid,
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

  ColumnFilters<String> get scope => $composableBuilder(
    column: $table.scope,
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

  ColumnFilters<int> get moduleId => $composableBuilder(
    column: $table.moduleId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get validFrom => $composableBuilder(
    column: $table.validFrom,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get validTo => $composableBuilder(
    column: $table.validTo,
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

  ColumnOrderings<String> get scope => $composableBuilder(
    column: $table.scope,
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

  ColumnOrderings<int> get moduleId => $composableBuilder(
    column: $table.moduleId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get validFrom => $composableBuilder(
    column: $table.validFrom,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get validTo => $composableBuilder(
    column: $table.validTo,
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

  GeneratedColumn<String> get scope =>
      $composableBuilder(column: $table.scope, builder: (column) => column);

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

  GeneratedColumn<int> get moduleId =>
      $composableBuilder(column: $table.moduleId, builder: (column) => column);

  GeneratedColumn<String> get validFrom =>
      $composableBuilder(column: $table.validFrom, builder: (column) => column);

  GeneratedColumn<String> get validTo =>
      $composableBuilder(column: $table.validTo, builder: (column) => column);
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
                Value<String> scope = const Value.absent(),
                Value<int> groupId = const Value.absent(),
                Value<int> weekday = const Value.absent(),
                Value<int> pairNumber = const Value.absent(),
                Value<String> startsAt = const Value.absent(),
                Value<String> endsAt = const Value.absent(),
                Value<String> subject = const Value.absent(),
                Value<String?> room = const Value.absent(),
                Value<String?> weekType = const Value.absent(),
                Value<int> subgroup = const Value.absent(),
                Value<String?> teacherName = const Value.absent(),
                Value<int?> moduleId = const Value.absent(),
                Value<String?> validFrom = const Value.absent(),
                Value<String?> validTo = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedLessonsCompanion(
                id: id,
                scope: scope,
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
                moduleId: moduleId,
                validFrom: validFrom,
                validTo: validTo,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required int id,
                required String scope,
                required int groupId,
                required int weekday,
                required int pairNumber,
                required String startsAt,
                required String endsAt,
                required String subject,
                Value<String?> room = const Value.absent(),
                Value<String?> weekType = const Value.absent(),
                required int subgroup,
                Value<String?> teacherName = const Value.absent(),
                Value<int?> moduleId = const Value.absent(),
                Value<String?> validFrom = const Value.absent(),
                Value<String?> validTo = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedLessonsCompanion.insert(
                id: id,
                scope: scope,
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
                moduleId: moduleId,
                validFrom: validFrom,
                validTo: validTo,
                rowid: rowid,
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
typedef $$CachedModulesTableCreateCompanionBuilder =
    CachedModulesCompanion Function({
      required String scope,
      required int moduleId,
      Value<String?> name,
      required String dateFrom,
      required String dateTo,
      Value<int> rowid,
    });
typedef $$CachedModulesTableUpdateCompanionBuilder =
    CachedModulesCompanion Function({
      Value<String> scope,
      Value<int> moduleId,
      Value<String?> name,
      Value<String> dateFrom,
      Value<String> dateTo,
      Value<int> rowid,
    });

class $$CachedModulesTableFilterComposer
    extends Composer<_$AppDatabase, $CachedModulesTable> {
  $$CachedModulesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get scope => $composableBuilder(
    column: $table.scope,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get moduleId => $composableBuilder(
    column: $table.moduleId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dateFrom => $composableBuilder(
    column: $table.dateFrom,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dateTo => $composableBuilder(
    column: $table.dateTo,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedModulesTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedModulesTable> {
  $$CachedModulesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get scope => $composableBuilder(
    column: $table.scope,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get moduleId => $composableBuilder(
    column: $table.moduleId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dateFrom => $composableBuilder(
    column: $table.dateFrom,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dateTo => $composableBuilder(
    column: $table.dateTo,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedModulesTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedModulesTable> {
  $$CachedModulesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get scope =>
      $composableBuilder(column: $table.scope, builder: (column) => column);

  GeneratedColumn<int> get moduleId =>
      $composableBuilder(column: $table.moduleId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get dateFrom =>
      $composableBuilder(column: $table.dateFrom, builder: (column) => column);

  GeneratedColumn<String> get dateTo =>
      $composableBuilder(column: $table.dateTo, builder: (column) => column);
}

class $$CachedModulesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedModulesTable,
          CachedModule,
          $$CachedModulesTableFilterComposer,
          $$CachedModulesTableOrderingComposer,
          $$CachedModulesTableAnnotationComposer,
          $$CachedModulesTableCreateCompanionBuilder,
          $$CachedModulesTableUpdateCompanionBuilder,
          (
            CachedModule,
            BaseReferences<_$AppDatabase, $CachedModulesTable, CachedModule>,
          ),
          CachedModule,
          PrefetchHooks Function()
        > {
  $$CachedModulesTableTableManager(_$AppDatabase db, $CachedModulesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedModulesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedModulesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedModulesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> scope = const Value.absent(),
                Value<int> moduleId = const Value.absent(),
                Value<String?> name = const Value.absent(),
                Value<String> dateFrom = const Value.absent(),
                Value<String> dateTo = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedModulesCompanion(
                scope: scope,
                moduleId: moduleId,
                name: name,
                dateFrom: dateFrom,
                dateTo: dateTo,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String scope,
                required int moduleId,
                Value<String?> name = const Value.absent(),
                required String dateFrom,
                required String dateTo,
                Value<int> rowid = const Value.absent(),
              }) => CachedModulesCompanion.insert(
                scope: scope,
                moduleId: moduleId,
                name: name,
                dateFrom: dateFrom,
                dateTo: dateTo,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedModulesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedModulesTable,
      CachedModule,
      $$CachedModulesTableFilterComposer,
      $$CachedModulesTableOrderingComposer,
      $$CachedModulesTableAnnotationComposer,
      $$CachedModulesTableCreateCompanionBuilder,
      $$CachedModulesTableUpdateCompanionBuilder,
      (
        CachedModule,
        BaseReferences<_$AppDatabase, $CachedModulesTable, CachedModule>,
      ),
      CachedModule,
      PrefetchHooks Function()
    >;
typedef $$CachedWeekCalendarTableCreateCompanionBuilder =
    CachedWeekCalendarCompanion Function({
      required String scope,
      required String dateFrom,
      required String dateTo,
      required String weekType,
      Value<int> rowid,
    });
typedef $$CachedWeekCalendarTableUpdateCompanionBuilder =
    CachedWeekCalendarCompanion Function({
      Value<String> scope,
      Value<String> dateFrom,
      Value<String> dateTo,
      Value<String> weekType,
      Value<int> rowid,
    });

class $$CachedWeekCalendarTableFilterComposer
    extends Composer<_$AppDatabase, $CachedWeekCalendarTable> {
  $$CachedWeekCalendarTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get scope => $composableBuilder(
    column: $table.scope,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dateFrom => $composableBuilder(
    column: $table.dateFrom,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dateTo => $composableBuilder(
    column: $table.dateTo,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get weekType => $composableBuilder(
    column: $table.weekType,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedWeekCalendarTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedWeekCalendarTable> {
  $$CachedWeekCalendarTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get scope => $composableBuilder(
    column: $table.scope,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dateFrom => $composableBuilder(
    column: $table.dateFrom,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dateTo => $composableBuilder(
    column: $table.dateTo,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get weekType => $composableBuilder(
    column: $table.weekType,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedWeekCalendarTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedWeekCalendarTable> {
  $$CachedWeekCalendarTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get scope =>
      $composableBuilder(column: $table.scope, builder: (column) => column);

  GeneratedColumn<String> get dateFrom =>
      $composableBuilder(column: $table.dateFrom, builder: (column) => column);

  GeneratedColumn<String> get dateTo =>
      $composableBuilder(column: $table.dateTo, builder: (column) => column);

  GeneratedColumn<String> get weekType =>
      $composableBuilder(column: $table.weekType, builder: (column) => column);
}

class $$CachedWeekCalendarTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedWeekCalendarTable,
          CachedWeekCalendarData,
          $$CachedWeekCalendarTableFilterComposer,
          $$CachedWeekCalendarTableOrderingComposer,
          $$CachedWeekCalendarTableAnnotationComposer,
          $$CachedWeekCalendarTableCreateCompanionBuilder,
          $$CachedWeekCalendarTableUpdateCompanionBuilder,
          (
            CachedWeekCalendarData,
            BaseReferences<
              _$AppDatabase,
              $CachedWeekCalendarTable,
              CachedWeekCalendarData
            >,
          ),
          CachedWeekCalendarData,
          PrefetchHooks Function()
        > {
  $$CachedWeekCalendarTableTableManager(
    _$AppDatabase db,
    $CachedWeekCalendarTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedWeekCalendarTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedWeekCalendarTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedWeekCalendarTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> scope = const Value.absent(),
                Value<String> dateFrom = const Value.absent(),
                Value<String> dateTo = const Value.absent(),
                Value<String> weekType = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedWeekCalendarCompanion(
                scope: scope,
                dateFrom: dateFrom,
                dateTo: dateTo,
                weekType: weekType,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String scope,
                required String dateFrom,
                required String dateTo,
                required String weekType,
                Value<int> rowid = const Value.absent(),
              }) => CachedWeekCalendarCompanion.insert(
                scope: scope,
                dateFrom: dateFrom,
                dateTo: dateTo,
                weekType: weekType,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedWeekCalendarTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedWeekCalendarTable,
      CachedWeekCalendarData,
      $$CachedWeekCalendarTableFilterComposer,
      $$CachedWeekCalendarTableOrderingComposer,
      $$CachedWeekCalendarTableAnnotationComposer,
      $$CachedWeekCalendarTableCreateCompanionBuilder,
      $$CachedWeekCalendarTableUpdateCompanionBuilder,
      (
        CachedWeekCalendarData,
        BaseReferences<
          _$AppDatabase,
          $CachedWeekCalendarTable,
          CachedWeekCalendarData
        >,
      ),
      CachedWeekCalendarData,
      PrefetchHooks Function()
    >;
typedef $$ScheduleCacheMetaTableCreateCompanionBuilder =
    ScheduleCacheMetaCompanion Function({
      required String scope,
      Value<String?> etag,
      required DateTime syncedAt,
      Value<int> rowid,
    });
typedef $$ScheduleCacheMetaTableUpdateCompanionBuilder =
    ScheduleCacheMetaCompanion Function({
      Value<String> scope,
      Value<String?> etag,
      Value<DateTime> syncedAt,
      Value<int> rowid,
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
  ColumnFilters<String> get scope => $composableBuilder(
    column: $table.scope,
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
  ColumnOrderings<String> get scope => $composableBuilder(
    column: $table.scope,
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
  GeneratedColumn<String> get scope =>
      $composableBuilder(column: $table.scope, builder: (column) => column);

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
                Value<String> scope = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                Value<DateTime> syncedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => ScheduleCacheMetaCompanion(
                scope: scope,
                etag: etag,
                syncedAt: syncedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String scope,
                Value<String?> etag = const Value.absent(),
                required DateTime syncedAt,
                Value<int> rowid = const Value.absent(),
              }) => ScheduleCacheMetaCompanion.insert(
                scope: scope,
                etag: etag,
                syncedAt: syncedAt,
                rowid: rowid,
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
typedef $$CachedExamsTableCreateCompanionBuilder =
    CachedExamsCompanion Function({
      Value<int> id,
      required int groupId,
      required String subject,
      Value<String?> teacher,
      Value<String?> consultationAt,
      Value<String?> examAt,
      Value<String?> room,
      Value<String?> kind,
    });
typedef $$CachedExamsTableUpdateCompanionBuilder =
    CachedExamsCompanion Function({
      Value<int> id,
      Value<int> groupId,
      Value<String> subject,
      Value<String?> teacher,
      Value<String?> consultationAt,
      Value<String?> examAt,
      Value<String?> room,
      Value<String?> kind,
    });

class $$CachedExamsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedExamsTable> {
  $$CachedExamsTableFilterComposer({
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

  ColumnFilters<String> get subject => $composableBuilder(
    column: $table.subject,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get teacher => $composableBuilder(
    column: $table.teacher,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get consultationAt => $composableBuilder(
    column: $table.consultationAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get examAt => $composableBuilder(
    column: $table.examAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get room => $composableBuilder(
    column: $table.room,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get kind => $composableBuilder(
    column: $table.kind,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedExamsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedExamsTable> {
  $$CachedExamsTableOrderingComposer({
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

  ColumnOrderings<String> get subject => $composableBuilder(
    column: $table.subject,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get teacher => $composableBuilder(
    column: $table.teacher,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get consultationAt => $composableBuilder(
    column: $table.consultationAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get examAt => $composableBuilder(
    column: $table.examAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get room => $composableBuilder(
    column: $table.room,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get kind => $composableBuilder(
    column: $table.kind,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedExamsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedExamsTable> {
  $$CachedExamsTableAnnotationComposer({
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

  GeneratedColumn<String> get subject =>
      $composableBuilder(column: $table.subject, builder: (column) => column);

  GeneratedColumn<String> get teacher =>
      $composableBuilder(column: $table.teacher, builder: (column) => column);

  GeneratedColumn<String> get consultationAt => $composableBuilder(
    column: $table.consultationAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get examAt =>
      $composableBuilder(column: $table.examAt, builder: (column) => column);

  GeneratedColumn<String> get room =>
      $composableBuilder(column: $table.room, builder: (column) => column);

  GeneratedColumn<String> get kind =>
      $composableBuilder(column: $table.kind, builder: (column) => column);
}

class $$CachedExamsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedExamsTable,
          CachedExam,
          $$CachedExamsTableFilterComposer,
          $$CachedExamsTableOrderingComposer,
          $$CachedExamsTableAnnotationComposer,
          $$CachedExamsTableCreateCompanionBuilder,
          $$CachedExamsTableUpdateCompanionBuilder,
          (
            CachedExam,
            BaseReferences<_$AppDatabase, $CachedExamsTable, CachedExam>,
          ),
          CachedExam,
          PrefetchHooks Function()
        > {
  $$CachedExamsTableTableManager(_$AppDatabase db, $CachedExamsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedExamsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedExamsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedExamsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> groupId = const Value.absent(),
                Value<String> subject = const Value.absent(),
                Value<String?> teacher = const Value.absent(),
                Value<String?> consultationAt = const Value.absent(),
                Value<String?> examAt = const Value.absent(),
                Value<String?> room = const Value.absent(),
                Value<String?> kind = const Value.absent(),
              }) => CachedExamsCompanion(
                id: id,
                groupId: groupId,
                subject: subject,
                teacher: teacher,
                consultationAt: consultationAt,
                examAt: examAt,
                room: room,
                kind: kind,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int groupId,
                required String subject,
                Value<String?> teacher = const Value.absent(),
                Value<String?> consultationAt = const Value.absent(),
                Value<String?> examAt = const Value.absent(),
                Value<String?> room = const Value.absent(),
                Value<String?> kind = const Value.absent(),
              }) => CachedExamsCompanion.insert(
                id: id,
                groupId: groupId,
                subject: subject,
                teacher: teacher,
                consultationAt: consultationAt,
                examAt: examAt,
                room: room,
                kind: kind,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedExamsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedExamsTable,
      CachedExam,
      $$CachedExamsTableFilterComposer,
      $$CachedExamsTableOrderingComposer,
      $$CachedExamsTableAnnotationComposer,
      $$CachedExamsTableCreateCompanionBuilder,
      $$CachedExamsTableUpdateCompanionBuilder,
      (
        CachedExam,
        BaseReferences<_$AppDatabase, $CachedExamsTable, CachedExam>,
      ),
      CachedExam,
      PrefetchHooks Function()
    >;
typedef $$ExamCacheMetaTableCreateCompanionBuilder =
    ExamCacheMetaCompanion Function({
      Value<int> groupId,
      Value<String?> etag,
      required DateTime syncedAt,
    });
typedef $$ExamCacheMetaTableUpdateCompanionBuilder =
    ExamCacheMetaCompanion Function({
      Value<int> groupId,
      Value<String?> etag,
      Value<DateTime> syncedAt,
    });

class $$ExamCacheMetaTableFilterComposer
    extends Composer<_$AppDatabase, $ExamCacheMetaTable> {
  $$ExamCacheMetaTableFilterComposer({
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

class $$ExamCacheMetaTableOrderingComposer
    extends Composer<_$AppDatabase, $ExamCacheMetaTable> {
  $$ExamCacheMetaTableOrderingComposer({
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

class $$ExamCacheMetaTableAnnotationComposer
    extends Composer<_$AppDatabase, $ExamCacheMetaTable> {
  $$ExamCacheMetaTableAnnotationComposer({
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

class $$ExamCacheMetaTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ExamCacheMetaTable,
          ExamCacheMetaData,
          $$ExamCacheMetaTableFilterComposer,
          $$ExamCacheMetaTableOrderingComposer,
          $$ExamCacheMetaTableAnnotationComposer,
          $$ExamCacheMetaTableCreateCompanionBuilder,
          $$ExamCacheMetaTableUpdateCompanionBuilder,
          (
            ExamCacheMetaData,
            BaseReferences<
              _$AppDatabase,
              $ExamCacheMetaTable,
              ExamCacheMetaData
            >,
          ),
          ExamCacheMetaData,
          PrefetchHooks Function()
        > {
  $$ExamCacheMetaTableTableManager(_$AppDatabase db, $ExamCacheMetaTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ExamCacheMetaTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ExamCacheMetaTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ExamCacheMetaTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> groupId = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                Value<DateTime> syncedAt = const Value.absent(),
              }) => ExamCacheMetaCompanion(
                groupId: groupId,
                etag: etag,
                syncedAt: syncedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> groupId = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                required DateTime syncedAt,
              }) => ExamCacheMetaCompanion.insert(
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

typedef $$ExamCacheMetaTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ExamCacheMetaTable,
      ExamCacheMetaData,
      $$ExamCacheMetaTableFilterComposer,
      $$ExamCacheMetaTableOrderingComposer,
      $$ExamCacheMetaTableAnnotationComposer,
      $$ExamCacheMetaTableCreateCompanionBuilder,
      $$ExamCacheMetaTableUpdateCompanionBuilder,
      (
        ExamCacheMetaData,
        BaseReferences<_$AppDatabase, $ExamCacheMetaTable, ExamCacheMetaData>,
      ),
      ExamCacheMetaData,
      PrefetchHooks Function()
    >;
typedef $$CachedNewsTableCreateCompanionBuilder =
    CachedNewsCompanion Function({
      Value<int> id,
      required String title,
      required String body,
      required String source,
      required String url,
      Value<String?> imageUrl,
      required bool isImportant,
      required DateTime publishedAt,
    });
typedef $$CachedNewsTableUpdateCompanionBuilder =
    CachedNewsCompanion Function({
      Value<int> id,
      Value<String> title,
      Value<String> body,
      Value<String> source,
      Value<String> url,
      Value<String?> imageUrl,
      Value<bool> isImportant,
      Value<DateTime> publishedAt,
    });

class $$CachedNewsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedNewsTable> {
  $$CachedNewsTableFilterComposer({
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

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get body => $composableBuilder(
    column: $table.body,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get url => $composableBuilder(
    column: $table.url,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get imageUrl => $composableBuilder(
    column: $table.imageUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isImportant => $composableBuilder(
    column: $table.isImportant,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get publishedAt => $composableBuilder(
    column: $table.publishedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedNewsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedNewsTable> {
  $$CachedNewsTableOrderingComposer({
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

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get body => $composableBuilder(
    column: $table.body,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get url => $composableBuilder(
    column: $table.url,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get imageUrl => $composableBuilder(
    column: $table.imageUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isImportant => $composableBuilder(
    column: $table.isImportant,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get publishedAt => $composableBuilder(
    column: $table.publishedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedNewsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedNewsTable> {
  $$CachedNewsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get body =>
      $composableBuilder(column: $table.body, builder: (column) => column);

  GeneratedColumn<String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);

  GeneratedColumn<String> get url =>
      $composableBuilder(column: $table.url, builder: (column) => column);

  GeneratedColumn<String> get imageUrl =>
      $composableBuilder(column: $table.imageUrl, builder: (column) => column);

  GeneratedColumn<bool> get isImportant => $composableBuilder(
    column: $table.isImportant,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get publishedAt => $composableBuilder(
    column: $table.publishedAt,
    builder: (column) => column,
  );
}

class $$CachedNewsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedNewsTable,
          CachedNew,
          $$CachedNewsTableFilterComposer,
          $$CachedNewsTableOrderingComposer,
          $$CachedNewsTableAnnotationComposer,
          $$CachedNewsTableCreateCompanionBuilder,
          $$CachedNewsTableUpdateCompanionBuilder,
          (
            CachedNew,
            BaseReferences<_$AppDatabase, $CachedNewsTable, CachedNew>,
          ),
          CachedNew,
          PrefetchHooks Function()
        > {
  $$CachedNewsTableTableManager(_$AppDatabase db, $CachedNewsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedNewsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedNewsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedNewsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> title = const Value.absent(),
                Value<String> body = const Value.absent(),
                Value<String> source = const Value.absent(),
                Value<String> url = const Value.absent(),
                Value<String?> imageUrl = const Value.absent(),
                Value<bool> isImportant = const Value.absent(),
                Value<DateTime> publishedAt = const Value.absent(),
              }) => CachedNewsCompanion(
                id: id,
                title: title,
                body: body,
                source: source,
                url: url,
                imageUrl: imageUrl,
                isImportant: isImportant,
                publishedAt: publishedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String title,
                required String body,
                required String source,
                required String url,
                Value<String?> imageUrl = const Value.absent(),
                required bool isImportant,
                required DateTime publishedAt,
              }) => CachedNewsCompanion.insert(
                id: id,
                title: title,
                body: body,
                source: source,
                url: url,
                imageUrl: imageUrl,
                isImportant: isImportant,
                publishedAt: publishedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedNewsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedNewsTable,
      CachedNew,
      $$CachedNewsTableFilterComposer,
      $$CachedNewsTableOrderingComposer,
      $$CachedNewsTableAnnotationComposer,
      $$CachedNewsTableCreateCompanionBuilder,
      $$CachedNewsTableUpdateCompanionBuilder,
      (CachedNew, BaseReferences<_$AppDatabase, $CachedNewsTable, CachedNew>),
      CachedNew,
      PrefetchHooks Function()
    >;
typedef $$CachedContactsTableCreateCompanionBuilder =
    CachedContactsCompanion Function({
      Value<int> id,
      required String section,
      required String name,
      Value<String?> role,
      Value<String?> office,
      Value<String?> email,
      Value<String?> phone,
      Value<String?> officeHours,
    });
typedef $$CachedContactsTableUpdateCompanionBuilder =
    CachedContactsCompanion Function({
      Value<int> id,
      Value<String> section,
      Value<String> name,
      Value<String?> role,
      Value<String?> office,
      Value<String?> email,
      Value<String?> phone,
      Value<String?> officeHours,
    });

class $$CachedContactsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedContactsTable> {
  $$CachedContactsTableFilterComposer({
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

  ColumnFilters<String> get section => $composableBuilder(
    column: $table.section,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get role => $composableBuilder(
    column: $table.role,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get office => $composableBuilder(
    column: $table.office,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get email => $composableBuilder(
    column: $table.email,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get phone => $composableBuilder(
    column: $table.phone,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get officeHours => $composableBuilder(
    column: $table.officeHours,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedContactsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedContactsTable> {
  $$CachedContactsTableOrderingComposer({
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

  ColumnOrderings<String> get section => $composableBuilder(
    column: $table.section,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get role => $composableBuilder(
    column: $table.role,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get office => $composableBuilder(
    column: $table.office,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get email => $composableBuilder(
    column: $table.email,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get phone => $composableBuilder(
    column: $table.phone,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get officeHours => $composableBuilder(
    column: $table.officeHours,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedContactsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedContactsTable> {
  $$CachedContactsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get section =>
      $composableBuilder(column: $table.section, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get role =>
      $composableBuilder(column: $table.role, builder: (column) => column);

  GeneratedColumn<String> get office =>
      $composableBuilder(column: $table.office, builder: (column) => column);

  GeneratedColumn<String> get email =>
      $composableBuilder(column: $table.email, builder: (column) => column);

  GeneratedColumn<String> get phone =>
      $composableBuilder(column: $table.phone, builder: (column) => column);

  GeneratedColumn<String> get officeHours => $composableBuilder(
    column: $table.officeHours,
    builder: (column) => column,
  );
}

class $$CachedContactsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedContactsTable,
          CachedContact,
          $$CachedContactsTableFilterComposer,
          $$CachedContactsTableOrderingComposer,
          $$CachedContactsTableAnnotationComposer,
          $$CachedContactsTableCreateCompanionBuilder,
          $$CachedContactsTableUpdateCompanionBuilder,
          (
            CachedContact,
            BaseReferences<_$AppDatabase, $CachedContactsTable, CachedContact>,
          ),
          CachedContact,
          PrefetchHooks Function()
        > {
  $$CachedContactsTableTableManager(
    _$AppDatabase db,
    $CachedContactsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedContactsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedContactsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedContactsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> section = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<String?> role = const Value.absent(),
                Value<String?> office = const Value.absent(),
                Value<String?> email = const Value.absent(),
                Value<String?> phone = const Value.absent(),
                Value<String?> officeHours = const Value.absent(),
              }) => CachedContactsCompanion(
                id: id,
                section: section,
                name: name,
                role: role,
                office: office,
                email: email,
                phone: phone,
                officeHours: officeHours,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String section,
                required String name,
                Value<String?> role = const Value.absent(),
                Value<String?> office = const Value.absent(),
                Value<String?> email = const Value.absent(),
                Value<String?> phone = const Value.absent(),
                Value<String?> officeHours = const Value.absent(),
              }) => CachedContactsCompanion.insert(
                id: id,
                section: section,
                name: name,
                role: role,
                office: office,
                email: email,
                phone: phone,
                officeHours: officeHours,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedContactsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedContactsTable,
      CachedContact,
      $$CachedContactsTableFilterComposer,
      $$CachedContactsTableOrderingComposer,
      $$CachedContactsTableAnnotationComposer,
      $$CachedContactsTableCreateCompanionBuilder,
      $$CachedContactsTableUpdateCompanionBuilder,
      (
        CachedContact,
        BaseReferences<_$AppDatabase, $CachedContactsTable, CachedContact>,
      ),
      CachedContact,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$CachedLessonsTableTableManager get cachedLessons =>
      $$CachedLessonsTableTableManager(_db, _db.cachedLessons);
  $$CachedModulesTableTableManager get cachedModules =>
      $$CachedModulesTableTableManager(_db, _db.cachedModules);
  $$CachedWeekCalendarTableTableManager get cachedWeekCalendar =>
      $$CachedWeekCalendarTableTableManager(_db, _db.cachedWeekCalendar);
  $$ScheduleCacheMetaTableTableManager get scheduleCacheMeta =>
      $$ScheduleCacheMetaTableTableManager(_db, _db.scheduleCacheMeta);
  $$CachedExamsTableTableManager get cachedExams =>
      $$CachedExamsTableTableManager(_db, _db.cachedExams);
  $$ExamCacheMetaTableTableManager get examCacheMeta =>
      $$ExamCacheMetaTableTableManager(_db, _db.examCacheMeta);
  $$CachedNewsTableTableManager get cachedNews =>
      $$CachedNewsTableTableManager(_db, _db.cachedNews);
  $$CachedContactsTableTableManager get cachedContacts =>
      $$CachedContactsTableTableManager(_db, _db.cachedContacts);
}
